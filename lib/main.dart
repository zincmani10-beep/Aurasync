import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';

/// Your hosted AuraSync (Streamlit Community Cloud).
const String kAuraUrl = 'https://aurasync-luxury-ambient.streamlit.app';

const Color kObsidian = Color(0xFF090A0E);
const Color kGold = Color(0xFFE5C378);

void main() => runApp(const AuraApp());

class AuraApp extends StatelessWidget {
  const AuraApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'AuraSync',
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark(useMaterial3: true).copyWith(
          scaffoldBackgroundColor: kObsidian,
          colorScheme: const ColorScheme.dark(primary: kGold),
        ),
        home: const AuraHome(),
      );
}

class AuraHome extends StatefulWidget {
  const AuraHome({super.key});
  @override
  State<AuraHome> createState() => _AuraHomeState();
}

/// Progress of one step in the "Set up everything" sheet.
enum _Stage { waiting, running, ok, warn }

class _SetupStep {
  _SetupStep(this.title, this.why);
  final String title;
  final String why;
  _Stage stage = _Stage.waiting;
  String note = '';
}

class _Res {
  const _Res(this.ok, this.note);
  final bool ok;
  final String note;
}

class _AuraHomeState extends State<AuraHome> {
  late final WebViewController _web;
  bool _loading = true;
  bool _failed = false;
  bool _setupRunning = false;

  // WiZ bulbs found by the last search (sent to the page with the next update)
  List<String>? _wizFound;

  // Always-on service: where heart-rate readings are also sent (set by the page)
  String _ingestUrl = '';
  String _ingestKey = '';
  DateTime _lastIngest = DateTime.fromMillisecondsSinceEpoch(0);

  // Bluetooth heart-rate state
  static final Guid _hrService = Guid('180D');
  static final Guid _hrChar = Guid('2A37');
  BluetoothDevice? _device;
  StreamSubscription<List<int>>? _hrSub;
  StreamSubscription<BluetoothConnectionState>? _connSub;
  int _bpm = 0;
  String _btState = 'idle'; // idle | scanning | connected | disconnected | error
  DateTime _lastPush = DateTime.fromMillisecondsSinceEpoch(0);
  final List<int> _rr = [];

  @override
  void initState() {
    super.initState();
    final host = Uri.parse(kAuraUrl).host;
    _web = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(kObsidian)
      // The page talks to the phone through this channel (see FLUTTER_BRIDGE.md):
      // device commands, and the heart-rate button on the page.
      ..addJavaScriptChannel('AuraNative', onMessageReceived: _onAuraMessage)
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) => setState(() {
          _loading = true;
          _failed = false;
        }),
        onPageFinished: (_) {
          setState(() => _loading = false);
          // Tell the page it is running inside the iPhone app, so it sends
          // light / fan / AC commands to this phone instead of the cloud server.
          Future.delayed(const Duration(seconds: 4), _push);
          Future.delayed(const Duration(seconds: 12), _push);
        },
        onWebResourceError: (e) {
          if (e.isForMainFrame ?? true) {
            setState(() {
              _failed = true;
              _loading = false;
            });
          }
        },
        onNavigationRequest: (req) {
          // Inner frames (Streamlit Cloud wraps the app in one) always load.
          if (!req.isMainFrame) return NavigationDecision.navigate;
          final u = Uri.tryParse(req.url);
          if (u == null) return NavigationDecision.prevent;
          final h = u.host;
          final ok = u.scheme == 'about' ||
              h == host ||
              h.endsWith('.streamlit.app') ||
              h == 'streamlit.io' ||
              h.endsWith('.streamlit.io');
          return ok ? NavigationDecision.navigate : NavigationDecision.prevent;
        },
      ))
      ..loadRequest(Uri.parse(kAuraUrl));
    WidgetsBinding.instance.addPostFrameCallback((_) => _reconnectLast());
  }

  @override
  void dispose() {
    _hrSub?.cancel();
    _connSub?.cancel();
    _device?.disconnect();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Messages from the page
  // ---------------------------------------------------------------------------
  Future<void> _onAuraMessage(JavaScriptMessage m) async {
    Map<String, dynamic> msg;
    try {
      msg = jsonDecode(m.message) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    switch (msg['t']) {
      case 'hr_connect':
        if (mounted) _openPicker();
        break;
      case 'hr_disconnect':
        await _disconnect();
        break;
      case 'cmd':
        if (msg['k'] == 'setup') {
          // The "Set up everything" button on the page.
          if (mounted) unawaited(_startSetup());
        } else if (msg['k'] == 'ingest') {
          _setIngest(msg);
        } else if (msg['k'] == 'hr_open') {
          if (mounted) _openPicker();
        } else if (msg['k'] == 'hr_off') {
          await _forgetBand();
          await _disconnect();
        } else if (msg['k'] == 'wiz_scan') {
          unawaited(_scanWiz());
        } else {
          await _runCommand(msg);
        }
        break;
    }
  }

  void _setIngest(Map<String, dynamic> c) {
    final u = Uri.tryParse('${c['url']}');
    final k = '${c['key']}';
    if (u != null && u.scheme == 'https' && k.length >= 20) {
      _ingestUrl = u.toString();
      _ingestKey = k;
    }
  }

  /// Sends the reading to the always-on service (at most every 10 seconds), so the home
  /// follows the heart rate even when the AuraSync page is not open.
  Future<void> _ingest(int hr) async {
    if (_ingestUrl.isEmpty) return;
    final now = DateTime.now();
    if (now.difference(_lastIngest).inSeconds < 10) return;
    _lastIngest = now;
    try {
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
      final req = await client.postUrl(Uri.parse(_ingestUrl));
      req.headers.contentType = ContentType.json;
      req.headers.set('Authorization', 'Bearer $_ingestKey');
      req.add(utf8.encode(jsonEncode({'hr': hr, 'tz': now.timeZoneOffset.inMinutes})));
      final res = await req.close();
      await res.drain<void>();
      client.close();
    } catch (_) {
      // No network for a moment must never crash the app.
    }
  }

  /// Only addresses inside a home network (or *.local names) may receive plain commands.
  bool _isPrivateHost(String host) {
    if (host.endsWith('.local')) return true;
    final a = InternetAddress.tryParse(host);
    if (a == null || a.type != InternetAddressType.IPv4) return false;
    final b = a.rawAddress;
    return b[0] == 10 ||
        (b[0] == 192 && b[1] == 168) ||
        (b[0] == 172 && b[1] >= 16 && b[1] <= 31) ||
        (b[0] == 169 && b[1] == 254);
  }

  Future<void> _runCommand(Map<String, dynamic> c) async {
    try {
      if (c['k'] == 'wiz') {
        final ip = '${c['ip']}';
        if (!_isPrivateHost(ip)) return;
        final sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
        sock.send(utf8.encode(jsonEncode(c['p'])), InternetAddress(ip), 38899);
        await Future.delayed(const Duration(milliseconds: 150));
        sock.close();
      } else if (c['k'] == 'http') {
        final uri = Uri.parse('${c['url']}');
        final plain = uri.scheme == 'http';
        if (plain && !_isPrivateHost(uri.host)) return; // never plain http to the internet
        if (!plain && uri.scheme != 'https') return;
        final client = HttpClient()..connectionTimeout = const Duration(seconds: 3);
        final req = await client.openUrl(
            '${c['method'] ?? 'POST'}'.toUpperCase(), uri);
        req.headers.contentType = ContentType.json;
        final hdr = c['headers'];
        if (hdr is Map) {
          hdr.forEach((k, v) => req.headers.set('$k', '$v'));
        }
        req.add(utf8.encode(jsonEncode(c['body'] ?? {})));
        final res = await req.close();
        await res.drain<void>();
        client.close();
      }
    } catch (_) {
      // A bulb that is offline must never crash the app.
    }
  }

  // ---------------------------------------------------------------------------
  // WiZ bulb search: asks every address on the home Wi-Fi (a unicast sweep, so no special
  // Apple networking entitlement is needed). A WiZ bulb answers getPilot.
  // ---------------------------------------------------------------------------
  Future<void> _scanWiz() async {
    _wizFound = null;
    final found = <String>{};
    try {
      String? ip;
      final ifs = await NetworkInterface.list(type: InternetAddressType.IPv4);
      for (final i in ifs) {
        if (i.name != 'en0') continue; // Wi-Fi
        for (final a in i.addresses) {
          if (_isPrivateHost(a.address)) ip = a.address;
        }
      }
      if (ip != null) {
        final p = ip.split('.');
        final prefix = '${p[0]}.${p[1]}.${p[2]}';
        final sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
        sock.listen((e) {
          if (e != RawSocketEvent.read) return;
          final d = sock.receive();
          if (d == null) return;
          try {
            final j = jsonDecode(utf8.decode(d.data));
            if (j is Map && j['result'] != null) found.add(d.address.address);
          } catch (_) {}
        }, onError: (_) {});
        final msg = utf8.encode(jsonEncode({'method': 'getPilot', 'params': {}}));
        for (var i = 1; i < 255; i++) {
          try {
            sock.send(msg, InternetAddress('$prefix.$i'), 38899);
          } catch (_) {}
          if (i % 40 == 0) await Future.delayed(const Duration(milliseconds: 30));
        }
        await Future.delayed(const Duration(seconds: 4));
        sock.close();
      }
    } catch (_) {}
    _wizFound = found.toList()..sort();
    await _push();
    _wizFound = null; // sent once
  }

  // ---------------------------------------------------------------------------
  // Remember the last heart-rate device and reconnect to it on its own
  // ---------------------------------------------------------------------------
  Future<void> _rememberBand(BluetoothDevice d) async {
    try {
      final sp = await SharedPreferences.getInstance();
      await sp.setString('last_band', d.remoteId.str);
    } catch (_) {}
  }

  Future<void> _forgetBand() async {
    try {
      final sp = await SharedPreferences.getInstance();
      await sp.remove('last_band');
    } catch (_) {}
  }

  Future<void> _reconnectLast() async {
    try {
      final sp = await SharedPreferences.getInstance();
      final id = sp.getString('last_band');
      if (id == null || id.isEmpty || _btState == 'connected') return;
      await _connect(BluetoothDevice.fromId(id), auto: true);
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // "Set up everything": one sheet, the iPhone permission prompts one after another
  // ---------------------------------------------------------------------------
  Future<_Res> _setupBluetooth() async {
    try {
      final s = await FlutterBluePlus.adapterState
          .firstWhere((x) => x != BluetoothAdapterState.unknown)
          .timeout(const Duration(seconds: 12));
      if (s == BluetoothAdapterState.unauthorized) {
        return const _Res(false, 'Blocked. Open iPhone Settings, AuraSync, and switch Bluetooth on.');
      }
      if (s == BluetoothAdapterState.off) {
        return const _Res(false, 'Bluetooth is switched off. Turn it on in Control Centre.');
      }
      if (s == BluetoothAdapterState.on) {
        return const _Res(true, 'Ready to find your heart-rate band.');
      }
      return const _Res(false, 'Bluetooth is not available on this device.');
    } catch (_) {
      return const _Res(false, 'No answer from Bluetooth. Try again.');
    }
  }

  Future<_Res> _setupLocalNetwork() async {
    try {
      String? ip;
      final ifs = await NetworkInterface.list(type: InternetAddressType.IPv4);
      for (final i in ifs) {
        if (i.name != 'en0') continue; // Wi-Fi
        for (final a in i.addresses) {
          if (_isPrivateHost(a.address)) ip = a.address;
        }
      }
      if (ip == null) {
        return const _Res(false, 'Join your home Wi-Fi, then tap Set up everything again.');
      }
      // A harmless packet to the router makes iPhone ask for Local Network access.
      final p = ip.split('.');
      p[3] = '1';
      final sock = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      sock.send(utf8.encode('aurasync'), InternetAddress(p.join('.')), 9);
      await Future.delayed(const Duration(seconds: 2));
      sock.close();
      return const _Res(true, 'Done. If iPhone asked, you tapped Allow.');
    } catch (_) {
      return const _Res(false, 'Could not reach your home network.');
    }
  }

  Future<void> _startSetup() async {
    if (_setupRunning || !mounted) return;
    _setupRunning = true;
    final steps = <_SetupStep>[
      _SetupStep('Bluetooth', 'Finds your heart-rate band'),
      _SetupStep('Home network', 'Lets AuraSync reach your lights, fan and AC'),
    ];
    final tick = ValueNotifier<int>(0);
    final actions = <Future<_Res> Function()>[_setupBluetooth, _setupLocalNetwork];

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF12141A),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => ValueListenableBuilder<int>(
        valueListenable: tick,
        builder: (_, __, ___) => _SetupSheet(steps: steps),
      ),
    );

    for (var i = 0; i < steps.length; i++) {
      steps[i].stage = _Stage.running;
      tick.value++;
      final r = await actions[i]();
      steps[i].stage = r.ok ? _Stage.ok : _Stage.warn;
      steps[i].note = r.note;
      tick.value++;
    }
    _setupRunning = false;
    await _push();
  }

  // ---- Push a reading into the hidden field the Streamlit app already watches
  // (same JSON contract as its Web Bluetooth path: {n, st, name, hr, rr, err}).
  Future<void> _push({int hr = 0, String? err}) async {
    final payload = {
      'n': DateTime.now().microsecondsSinceEpoch.toString(),
      'st': _btState,
      'name': _device?.platformName ?? '',
      'hr': hr,
      'rr': List<int>.from(_rr),
      'err': err ?? '',
      'src': 'Bluetooth 0x180D',
      'nat': 1, // "I am the iPhone app": the page then routes device commands through this phone
      if (_wizFound != null) 'wiz': _wizFound,
    };
    final js = '''
(function(p){
  function find(doc, depth){
    var el = doc.querySelector('.st-key-aura_hr_bridge input');
    if (el) return el;
    if (depth > 3) return null;
    var fr = doc.querySelectorAll('iframe');
    for (var i = 0; i < fr.length; i++){
      try {
        var d = fr[i].contentDocument;
        if (d){ var r = find(d, depth + 1); if (r) return r; }
      } catch (e) {}
    }
    return null;
  }
  var el = find(document, 0);
  if (!el) return 'no-input';
  var win = el.ownerDocument.defaultView;
  var set = Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype, 'value').set;
  set.call(el, JSON.stringify(p));
  el.dispatchEvent(new win.Event('input', {bubbles: true}));
  el.dispatchEvent(new win.KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  return 'ok';
})(${jsonEncode(payload)});
''';
    try {
      await _web.runJavaScript(js);
    } catch (_) {}
  }

  // ---- Heart Rate Measurement (0x2A37) parser
  void _onHrData(List<int> d) {
    if (d.length < 2) return;
    final flags = d[0];
    var i = 1;
    int hr;
    if (flags & 0x01 == 0) {
      hr = d[i];
      i += 1;
    } else {
      if (d.length < 3) return;
      hr = d[i] | (d[i + 1] << 8);
      i += 2;
    }
    if (flags & 0x08 != 0) i += 2; // energy expended
    if (flags & 0x10 != 0) {
      while (i + 1 < d.length) {
        final raw = d[i] | (d[i + 1] << 8);
        _rr.add((raw * 1000 / 1024).round());
        i += 2;
      }
      if (_rr.length > 60) _rr.removeRange(0, _rr.length - 60);
    }
    if (mounted) setState(() => _bpm = hr);
    final now = DateTime.now();
    if (now.difference(_lastPush).inMilliseconds >= 1000) {
      _lastPush = now;
      _push(hr: hr);
    }
    _ingest(hr);
  }

  Future<void> _connect(BluetoothDevice dev, {bool auto = false}) async {
    try {
      await FlutterBluePlus.stopScan();
      await dev.connect(timeout: Duration(seconds: auto ? 8 : 15));
      _device = dev;
      _connSub?.cancel();
      _connSub = dev.connectionState.listen((s) {
        if (s == BluetoothConnectionState.disconnected) {
          _btState = 'disconnected';
          if (mounted) setState(() => _bpm = 0);
          _push();
        }
      });
      final services = await dev.discoverServices();
      final svc = services.firstWhere((s) => s.uuid == _hrService);
      final ch = svc.characteristics.firstWhere((c) => c.uuid == _hrChar);
      await ch.setNotifyValue(true);
      _hrSub?.cancel();
      _hrSub = ch.lastValueStream.listen(_onHrData);
      _btState = 'connected';
      await _rememberBand(dev);
      if (mounted) setState(() {});
      await _push();
    } catch (e) {
      if (auto) return; // the saved band is simply not nearby: stay quiet
      _btState = 'error';
      if (mounted) setState(() {});
      await _push(err: 'connect');
    }
  }

  Future<void> _disconnect() async {
    await _hrSub?.cancel();
    await _device?.disconnect();
    _btState = 'disconnected';
    if (mounted) setState(() => _bpm = 0);
    await _push();
  }

  void _openPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF12141A),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _HrPicker(
        connected: _btState == 'connected',
        deviceName: _device?.platformName ?? '',
        bpm: _bpm,
        onConnect: (d) {
          Navigator.pop(context);
          _connect(d);
        },
        onDisconnect: () {
          Navigator.pop(context);
          _forgetBand();
          _disconnect();
        },
        hrService: _hrService,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final connected = _btState == 'connected';
    return Scaffold(
      body: SafeArea(
        child: Stack(children: [
          if (!_failed) WebViewWidget(controller: _web),
          if (_loading && !_failed)
            const Center(child: CircularProgressIndicator(color: kGold)),
          if (_failed)
            Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.cloud_off, color: kGold, size: 48),
                const SizedBox(height: 12),
                const Text('Can\u2019t reach AuraSync'),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: () {
                    setState(() => _failed = false);
                    _web.loadRequest(Uri.parse(kAuraUrl));
                  },
                  child: const Text('Try again'),
                ),
              ]),
            ),
        ]),
      ),
      floatingActionButton: _failed
          ? null
          : Padding(
              padding: const EdgeInsets.only(bottom: 56),
              child: FloatingActionButton.small(
                backgroundColor: connected ? kGold : const Color(0xFF1B1E26),
                foregroundColor: connected ? kObsidian : kGold,
                onPressed: _openPicker,
                child: connected
                    ? Text('$_bpm', style: const TextStyle(fontWeight: FontWeight.bold))
                    : const Icon(Icons.favorite_border),
              ),
            ),
    );
  }
}

/// The "Set up everything" progress sheet.
class _SetupSheet extends StatelessWidget {
  const _SetupSheet({required this.steps});
  final List<_SetupStep> steps;

  Widget _icon(_Stage s) {
    switch (s) {
      case _Stage.ok:
        return const Icon(Icons.check_circle, color: kGold);
      case _Stage.warn:
        return const Icon(Icons.error_outline, color: Colors.orangeAccent);
      case _Stage.running:
        return const SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2, color: kGold));
      case _Stage.waiting:
        return const Icon(Icons.radio_button_unchecked, color: Colors.white38);
    }
  }

  @override
  Widget build(BuildContext context) {
    final done = steps.every((s) => s.stage == _Stage.ok || s.stage == _Stage.warn);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Getting AuraSync ready',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: kGold)),
        const SizedBox(height: 4),
        const Text('Tap Allow when iPhone asks.', style: TextStyle(color: Colors.white70)),
        const SizedBox(height: 12),
        for (final s in steps)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: _icon(s.stage),
            title: Text(s.title),
            subtitle: Text(s.note.isEmpty ? s.why : s.note),
          ),
        if (done)
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Done')),
          ),
      ]),
    );
  }
}

class _HrPicker extends StatefulWidget {
  const _HrPicker({
    required this.connected,
    required this.deviceName,
    required this.bpm,
    required this.onConnect,
    required this.onDisconnect,
    required this.hrService,
  });
  final bool connected;
  final String deviceName;
  final int bpm;
  final void Function(BluetoothDevice) onConnect;
  final VoidCallback onDisconnect;
  final Guid hrService;
  @override
  State<_HrPicker> createState() => _HrPickerState();
}

class _HrPickerState extends State<_HrPicker> {
  List<ScanResult> _results = [];
  StreamSubscription<List<ScanResult>>? _sub;
  String? _msg;

  @override
  void initState() {
    super.initState();
    if (!widget.connected) _scan();
  }

  Future<void> _scan() async {
    try {
      if (await FlutterBluePlus.adapterState.first != BluetoothAdapterState.on) {
        setState(() => _msg = 'Turn Bluetooth on to find your heart-rate band.');
        return;
      }
      _sub = FlutterBluePlus.scanResults.listen((r) {
        if (mounted) setState(() => _results = r);
      });
      await FlutterBluePlus.startScan(
          withServices: [widget.hrService], timeout: const Duration(seconds: 12));
    } catch (_) {
      if (mounted) setState(() => _msg = 'Bluetooth scan failed. Check permission in Settings.');
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    FlutterBluePlus.stopScan();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(widget.connected ? 'Heart-rate band connected' : 'Connect a heart-rate band',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: kGold)),
        const SizedBox(height: 12),
        if (widget.connected) ...[
          Text('${widget.deviceName}  \u2022  ${widget.bpm} BPM'),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: widget.onDisconnect, child: const Text('Disconnect')),
        ] else ...[
          if (_msg != null) Text(_msg!),
          if (_msg == null && _results.isEmpty) const Text('Searching nearby\u2026'),
          for (final r in _results)
            ListTile(
              leading: const Icon(Icons.watch, color: kGold),
              title: Text(r.device.platformName.isEmpty ? 'Heart-rate sensor' : r.device.platformName),
              subtitle: Text('Signal ${r.rssi} dBm'),
              onTap: () => widget.onConnect(r.device),
            ),
        ],
      ]),
    );
  }
}
