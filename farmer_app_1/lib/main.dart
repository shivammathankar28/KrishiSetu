import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'services/api_service.dart';

void main() {
  runApp(const KrishiSetuApp());
}

class KrishiSetuApp extends StatelessWidget {
  const KrishiSetuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KrishiSetu Mandi Gateway',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const BookingScreen(),
    );
  }
}

class BookingScreen extends StatefulWidget {
  const BookingScreen({super.key});

  @override
  State<BookingScreen> createState() => _BookingScreenState();
}

class _BookingScreenState extends State<BookingScreen> {
  final _phoneController = TextEditingController(text: "9876543210");
  final _weightController = TextEditingController(text: "40");
  final _vehicleNoController = TextEditingController(text: "MH-31-TR-9044");

  String selectedCrop = "Soybean";
  String selectedVehicle = "Tractor Trolley";
  String selectedSlot = "08:00 - 10:00";
  bool isLoading = false;

  final Map<String, double> mspRates = {
    "Soybean": 4892.00,
    "Wheat": 2275.00,
    "Paddy (Rice)": 2300.00,
    "Cotton": 7121.00,
  };

  double get calculatedPayout {
    final weight = double.tryParse(_weightController.text) ?? 0;
    return (mspRates[selectedCrop] ?? 2000.0) * weight;
  }

  Future<void> handleBooking() async {
    setState(() => isLoading = true);
    try {
      final payload = {
        "farmer_phone": _phoneController.text.trim(),
        "commodity": selectedCrop,
        "weight_to_bring_quintals": double.parse(_weightController.text),
        "vehicle_type": selectedVehicle,
        "vehicle_number": _vehicleNoController.text.trim(),
        "preferred_slot": selectedSlot,
      };

      final response = await ApiService.bookSlot(payload);
      if (!mounted) return;

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => TokenPassScreen(tokenData: response['token']),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("KrishiSetu - Slot Booking", style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.green.shade800,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  children: [
                    TextField(
                      controller: _phoneController,
                      decoration: const InputDecoration(labelText: "Registered Phone Number", prefixIcon: Icon(Icons.phone)),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedCrop,
                      decoration: const InputDecoration(labelText: "Commodity", prefixIcon: Icon(Icons.eco)),
                      items: mspRates.keys.map((crop) => DropdownMenuItem(value: crop, child: Text("$crop (₹${mspRates[crop]}/Q)"))).toList(),
                      onChanged: (val) => setState(() => selectedCrop = val!),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _weightController,
                      decoration: const InputDecoration(labelText: "Quantity (Quintals)", prefixIcon: Icon(Icons.scale)),
                      keyboardType: TextInputType.number,
                      onChanged: (_) => setState(() {}),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedSlot,
                      decoration: const InputDecoration(labelText: "Preferred Time Slot", prefixIcon: Icon(Icons.schedule)),
                      items: const [
                        DropdownMenuItem(value: "08:00 - 10:00", child: Text("08:00 - 10:00")),
                        DropdownMenuItem(value: "10:00 - 12:00", child: Text("10:00 - 12:00")),
                        DropdownMenuItem(value: "12:00 - 14:00", child: Text("12:00 - 14:00")),
                        DropdownMenuItem(value: "14:00 - 16:00", child: Text("14:00 - 16:00")),
                      ],
                      onChanged: (val) => setState(() => selectedSlot = val!),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _vehicleNoController,
                      decoration: const InputDecoration(labelText: "Vehicle Number", prefixIcon: Icon(Icons.local_shipping)),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.green.shade200),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("Estimated MSP Payout:", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                  Text(
                    "₹${calculatedPayout.toStringAsFixed(2)}",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.green.shade900),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: isLoading ? null : handleBooking,
              icon: isLoading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Icon(Icons.send),
              label: Text(isLoading ? "Processing..." : "Submit Slot Request"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green.shade700,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class TokenPassScreen extends StatelessWidget {
  final Map<String, dynamic> tokenData;
  const TokenPassScreen({super.key, required this.tokenData});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Digital Mandi Pass"),
        backgroundColor: Colors.green.shade800,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            children: [
              Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      Text(tokenData['token_id'] ?? '', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                      const SizedBox(height: 6),
                      Text("Farmer: ${tokenData['farmer_name'] ?? ''}", style: const TextStyle(fontSize: 14, color: Colors.grey)),
                      const Divider(height: 30),
                      QrImageView(
                        data: tokenData['token_id'] ?? '',
                        version: QrVersions.auto,
                        size: 180.0,
                      ),
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Allotted Slot:", style: TextStyle(fontWeight: FontWeight.w500)),
                          Text(tokenData['allocated_slot'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Officer Status:", style: TextStyle(fontWeight: FontWeight.w500)),
                          Text(tokenData['officer_status'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.orange)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Live Stage:", style: TextStyle(fontWeight: FontWeight.w500)),
                          Text(tokenData['current_stage'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}