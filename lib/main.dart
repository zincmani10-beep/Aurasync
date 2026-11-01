import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
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

class _AuraHomeState extends State<AuraHome> {
  late final WebViewController _web;
  bool _loading = true;
  bool _failed = false;

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
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) => setState(() {
          _loading = true;
          _failed = false;
        }),
        onPageFinished: (_) => setState(() => _loading = false),
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
  }

  @override
  void dispose() {
    _hrSub?.cancel();
    _connSub?.cancel();
    _device?.disconnect();
    super.dispose();
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
  }

  Future<void> _connect(BluetoothDevice dev) async {
    try {
      await FlutterBluePlus.stopScan();
      await dev.connect(timeout: const Duration(seconds: 15));
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
      if (mounted) setState(() {});
      await _push();
    } catch (e) {
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
