import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  
  static const String baseUrl = "http://localhost:8000/api/v1";

  static Future<Map<String, dynamic>> registerFarmer(Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('$baseUrl/farmer/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Registration failed');
    }
  }

  static Future<Map<String, dynamic>> bookSlot(Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('$baseUrl/slots/book'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Booking failed');
    }
  }

  static Future<Map<String, dynamic>> getLiveMarketStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/market/live-status'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load market status');
    }
  }
}