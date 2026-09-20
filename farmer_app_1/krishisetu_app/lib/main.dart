import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

const String kBaseUrl = "https://stump-emphasis-deck.ngrok-free.dev";

// ---------------------------------------------------------
// NOTIFICATION SERVICE
// ---------------------------------------------------------
final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

Future<void> initNotifications() async {
  const AndroidInitializationSettings initializationSettingsAndroid = AndroidInitializationSettings('@mipmap/ic_launcher');
  const InitializationSettings initializationSettings = InitializationSettings(android: initializationSettingsAndroid);
  await flutterLocalNotificationsPlugin.initialize(initializationSettings);
}

Future<void> showLocalNotification(String title, String body) async {
  const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
    'mandi_updates_channel', 'Mandi Status Updates',
    channelDescription: 'Real-time notifications for APMC gate pass & queue status',
    importance: Importance.max, priority: Priority.high,
  );
  await flutterLocalNotificationsPlugin.show(0, title, body, const NotificationDetails(android: androidDetails));
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initNotifications();
  runApp(const FarmerApp());
}

// ---------------------------------------------------------
// 100% COMPREHENSIVE MULTI-LANGUAGE TRANSLATION DICTIONARY
// ---------------------------------------------------------
const Map<String, Map<String, String>> appTranslations = {
  'en': {
    'app_title': 'KrishiSetu App',
    'tagline': 'Direct APMC Farmer Procurement Portal',
    'select_lang': 'Select Language',
    'btn_login_existing': 'LOGIN (EXISTING FARMER)',
    'btn_create_acc': 'CREATE NEW FARMER ACCOUNT',
    'auth_welcome': 'Welcome Back! 👋',
    'auth_subtitle': 'Enter your registered phone number to receive OTP',
    'lbl_mobile': 'Mobile Number',
    'btn_send_otp': 'SEND VERIFICATION OTP',
    'reg_title': 'Farmer Details & Slot Booking',
    'reg_subtitle': 'Register your details to create an account and receive an official APMC gate pass.',
    'lbl_fullname': 'Full Name',
    'lbl_aadhaar': 'Aadhaar (Last 4 Digits)',
    'lbl_bank': 'Bank Account No.',
    'lbl_ifsc': 'Bank IFSC Code',
    'lbl_land': 'Land (Acres)',
    'lbl_village': 'Village / District',
    'lbl_stock': 'Total Harvest Stock (Quintals)',
    'lbl_commodity': 'Commodity / Crop',
    'lbl_weight': 'Weight to Bring (Quintals)',
    'lbl_vehicle_type': 'Vehicle Type',
    'lbl_veh_count': 'No. of Veh',
    'lbl_veh_plate': 'Vehicle Plate No.',
    'lbl_target_slot': 'Target Time Window',
    'lbl_procurement_center': 'Preferred Procurement Center',
    'house_full_alert': '🚨 HOUSE FULL: All slots for today are full. Try again tomorrow.',
    'btn_submit_pass': 'SUBMIT REQUEST & GET PASS',
    'otp_title': 'Enter Security OTP',
    'otp_subtitle': 'Verification code sent to +91',
    'btn_verify': 'VERIFY & CONTINUE',
    'live_queue': '🚜 Live Mandi Queue Status',
    'farmers_ahead': 'Farmers Ahead',
    'est_wait': 'Est. Wait Time',
    'tab_rates': 'Crop Rates',
    'tab_book': 'Book Slot',
    'tab_pass': 'My Gate Pass',
    'tab_profile': 'My Profile',
    'welcome_farmer': 'Welcome,',
    'msp_subtitle': 'Check official Minimum Support Prices (MSP) guaranteed by the government.',
    'msp_header': 'Current MSP Rates (2026 Season)',
    'gov_guarantee': 'Government Guaranteed Price',
    'btn_book_now': 'BOOK A PROCUREMENT SLOT NOW',
    'status_pending': 'DECISION: PENDING APPROVAL',
    'status_approved': 'DECISION: APPROVED',
    'status_rejected': 'DECISION: REJECTED',
    'status_pending_desc': 'Awaiting approval from the Procurement Officer.',
    'status_approved_desc': 'Your pass is approved. You may proceed to the APMC gate.',
    'status_rejected_desc': 'Your slot request was rejected by the officer.',
    'token_scanned': '✅ Token Scanned & Fully Processed',
    'live_stage_prog': 'Live Stage Progress',
    'stage_requested': 'Slot Request Sent',
    'stage_accepted': 'Gate Pass Approved',
    'stage_gate_in': 'Mandi Gate-In',
    'stage_assaying': 'Quality Assaying',
    'stage_weighment': 'Weighbridge Measurement',
    'stage_unloading': 'Yard Unloading',
    'stage_payment': 'DBT Payment Settlement',
    'stage_completed': 'Procurement Complete',
    'done': 'DONE',
    'in_progress': 'IN PROGRESS',
    'not_done': 'NOT DONE',
    'no_gate_pass': 'No active gate pass found.\nPlease book a slot to generate your pass.',
    'profile_info': 'Registered Account Info',
    'land_holding': 'Land Holding:',
    'total_stock': 'Total Stock:',
    'bank_acc': 'Bank Account No.:',
    'ifsc_code': 'IFSC Code:',
    'vehicle_plate': 'Vehicle Plate:',
    'center_label': 'Procurement Center:',
    'btn_logout': 'LOG OUT OF APP',
    'btn_download_receipt': 'DOWNLOAD OFFICIAL DBT RECEIPT',
    'receipt_dialog_title': 'Official DBT Payment Receipt',
    'receipt_dialog_close': 'Close',
    'refresh': 'Refresh',
    'token_id': 'Token ID',
    'farmer_name': 'Farmer Name',
    'vehicle': 'Vehicle'
  },
  'hi': {
    'app_title': 'कृषिसेतू ऐप',
    'tagline': 'प्रत्यक्ष एपीएमसी किसान खरीद पोर्टल',
    'select_lang': 'भाषा चुनें',
    'btn_login_existing': 'लॉगिन (मौजूदा किसान)',
    'btn_create_acc': 'नया किसान खाता बनाएं',
    'auth_welcome': 'वापस स्वागत है! 👋',
    'auth_subtitle': 'ओटीपी प्राप्त करने के लिए अपना पंजीकृत फोन नंबर दर्ज करें',
    'lbl_mobile': 'मोबाइल नंबर',
    'btn_send_otp': 'सत्यापन ओटीपी भेजें',
    'reg_title': 'किसान विवरण और स्लॉट बुकिंग',
    'reg_subtitle': 'खाता बनाने और आधिकारिक एपीएमसी गेट पास प्राप्त करने के लिए अपना विवरण दर्ज करें।',
    'lbl_fullname': 'पूरा नाम',
    'lbl_aadhaar': 'आधार (अंतिम 4 अंक)',
    'lbl_bank': 'बैंक खाता संख्या',
    'lbl_ifsc': 'बैंक IFSC कोड',
    'lbl_land': 'भूमि (एकड़)',
    'lbl_village': 'गांव / जिला',
    'lbl_stock': 'कुल फसल स्टॉक (क्विंटल)',
    'lbl_commodity': 'जिंस / फसल',
    'lbl_weight': 'लाने के लिए वजन (क्विंटल)',
    'lbl_vehicle_type': 'वाहन का प्रकार',
    'lbl_veh_count': 'वाहनों की संख्या',
    'lbl_veh_plate': 'वाहन प्लेट नंबर',
    'lbl_target_slot': 'लक्ष्य समय विंडो',
    'lbl_procurement_center': 'पसंदीदा खरीद केंद्र',
    'house_full_alert': '🚨 हाउस फुल: आज के सभी स्लॉट भर चुके हैं। कल पुनः प्रयास करें।',
    'btn_submit_pass': 'अनुरोध सबमिट करें और पास प्राप्त करें',
    'otp_title': 'सुरक्षा ओटीपी दर्ज करें',
    'otp_subtitle': 'सत्यापन कोड भेजा गया +91',
    'btn_verify': 'सत्यापित करें और आगे बढ़ें',
    'live_queue': '🚜 लाइव मंडी कतार स्थिति',
    'farmers_ahead': 'आगे किसान',
    'est_wait': 'अनुमानित प्रतीक्षा समय',
    'tab_rates': 'फसल दरें',
    'tab_book': 'स्लॉट बुक करें',
    'tab_pass': 'मेरा गेट पास',
    'tab_profile': 'मेरी प्रोफाइल',
    'welcome_farmer': 'स्वागत है,',
    'msp_subtitle': 'सरकार द्वारा गारंटीकृत आधिकारिक न्यूनतम समर्थन मूल्य (MSP) की जांच करें।',
    'msp_header': 'वर्तमान MSP दरें (2026 सीजन)',
    'gov_guarantee': 'सरकार समर्थित मूल्य',
    'btn_book_now': 'अभी खरीद स्लॉट बुक करें',
    'status_pending': 'निर्णय: अनुमोदन लंबित',
    'status_approved': 'निर्णय: स्वीकृत',
    'status_rejected': 'निर्णय: अस्वीकृत',
    'status_pending_desc': 'खरीद अधिकारी के अनुमोदन की प्रतीक्षा है।',
    'status_approved_desc': 'आपका पास स्वीकृत हो गया है। आप एपीएमसी गेट पर आगे बढ़ सकते हैं।',
    'status_rejected_desc': 'अधिकारी द्वारा आपका स्लॉट अनुरोध अस्वीकार कर दिया गया।',
    'token_scanned': '✅ टोकन स्कैन किया गया और पूरी तरह से प्रसंस्कृत',
    'live_stage_prog': 'लाइव चरण प्रगति',
    'stage_requested': 'स्लॉट अनुरोध भेजा गया',
    'stage_accepted': 'गेट पास स्वीकृत',
    'stage_gate_in': 'मंडी गेट-इन',
    'stage_assaying': 'गुणवत्ता परख',
    'stage_weighment': 'वेयब्रिज माप',
    'stage_unloading': 'यार्ड अनलोडिंग',
    'stage_payment': 'DBT भुगतान निपटान',
    'stage_completed': 'खरीद पूर्ण',
    'done': 'पूर्ण',
    'in_progress': 'प्रगति पर',
    'not_done': 'पूर्ण नहीं',
    'no_gate_pass': 'कोई सक्रिय गेट पास नहीं मिला।\nअपना पास जनरेट करने के लिए स्लॉट बुक करें।',
    'profile_info': 'पंजीकृत खाता जानकारी',
    'land_holding': 'भूमि धारक:',
    'total_stock': 'कुल स्टॉक:',
    'bank_acc': 'बैंक खाता संख्या:',
    'ifsc_code': 'IFSC कोड:',
    'vehicle_plate': 'वाहन प्लेट:',
    'center_label': 'खरीद केंद्र:',
    'btn_logout': 'ऐप से लॉग आउट करें',
    'btn_download_receipt': 'आधिकारिक DBT रसीद डाउनलोड करें',
    'receipt_dialog_title': 'आधिकारिक DBT भुगतान रसीद',
    'receipt_dialog_close': 'बंद करें',
    'refresh': 'रीफ्रेश',
    'token_id': 'टोकन आईडी',
    'farmer_name': 'किसान का नाम',
    'vehicle': 'वाहन'
  },
  'mr': {
    'app_title': 'कृषीसेतू ॲप',
    'tagline': 'थेट एपीएमसी शेतकरी खरेदी पोर्टल',
    'select_lang': 'भाषा निवडा',
    'btn_login_existing': 'लॉगिन (विद्यमान शेतकरी)',
    'btn_create_acc': 'नवीन शेतकरी खाते तयार करा',
    'auth_welcome': 'परत स्वागत आहे! 👋',
    'auth_subtitle': 'OTP मिळवण्यासाठी तुमचा नोंदणीकृत फोन नंबर प्रविष्ट करा',
    'lbl_mobile': 'मोबाईल नंबर',
    'btn_send_otp': 'पडताळणी OTP पाठवा',
    'reg_title': 'शेतकरी तपशील आणि स्लॉट बुकिंग',
    'reg_subtitle': 'खाते तयार करण्यासाठी आणि अधिकृत APMC गेट पास मिळवण्यासाठी तुमचे तपशील नोंदवा.',
    'lbl_fullname': 'पूर्ण नाव',
    'lbl_aadhaar': 'आधार (शेवटचे 4 अंक)',
    'lbl_bank': 'बँक खाते क्र.',
    'lbl_ifsc': 'बँक IFSC कोड',
    'lbl_land': 'जमीन (एकर)',
    'lbl_village': 'गाव / जिल्हा',
    'lbl_stock': 'एकूण पीक साठा (क्विंटल)',
    'lbl_commodity': 'शेतमाल / पीक',
    'lbl_weight': 'आणायचे वजन (क्विंटल)',
    'lbl_vehicle_type': 'वाहनाचा प्रकार',
    'lbl_veh_count': 'वाहनांची संख्या',
    'lbl_veh_plate': 'वाहन प्लेट क्र.',
    'lbl_target_slot': 'लक्ष्य वेळ विंडो',
    'lbl_procurement_center': 'पसंतीचे खरेदी केंद्र',
    'house_full_alert': '🚨 हाऊस फुल: आजचे सर्व स्लॉट भरले आहेत. उद्या पुन्हा प्रयत्न करा.',
    'btn_submit_pass': 'विनंती सबमिट करा आणि पास मिळवा',
    'otp_title': 'सुरक्षा OTP प्रविष्ट करा',
    'otp_subtitle': 'पडताळणी कोड पाठवला आहे +91',
    'btn_verify': 'सत्यापित करा आणि पुढे जा',
    'live_queue': '🚜 थेट मार्केट रांग स्थिती',
    'farmers_ahead': 'पुढील शेतकरी',
    'est_wait': 'अंदाजे प्रतीक्षा वेळ',
    'tab_rates': 'पिकांचे भाव',
    'tab_book': 'स्लॉट बुक करा',
    'tab_pass': 'माझा गेट पास',
    'tab_profile': 'माझे प्रोफाइल',
    'welcome_farmer': 'स्वागत आहे,',
    'msp_subtitle': 'सरकारतर्फे हमी दिलेले अधिकृत किमान आधारभूत मूल्य (MSP) तपासा.',
    'msp_header': 'सध्याचे MSP दर (२०२६ हंगाम)',
    'gov_guarantee': 'सरकार हमी मूल्य',
    'btn_book_now': 'आता खरेदी स्लॉट बुक करा',
    'status_pending': 'निर्णय: मंजुरी प्रलंबित',
    'status_approved': 'निर्णय: मंजूर',
    'status_rejected': 'निर्णय: नाकारले',
    'status_pending_desc': 'खरेदी अधिकाऱ्याच्या मंजुरीची प्रतीक्षा आहे.',
    'status_approved_desc': 'तुमचा पास मंजूर झाला आहे. तुम्ही APMC गेटकडे जाऊ शकता.',
    'status_rejected_desc': 'अधिकाऱ्याद्वारे तुमची स्लॉट विनंती नाकारण्यात आली.',
    'token_scanned': '✅ टोकन स्कॅन केले आणि पूर्णपणे प्रक्रिया केली',
    'live_stage_prog': 'थेट टप्पा प्रगती',
    'stage_requested': 'स्लॉट विनंती पाठवली',
    'stage_accepted': 'गेट पास मंजूर',
    'stage_gate_in': 'मंडी गेट-इन',
    'stage_assaying': 'गुणवत्ता तपासणी',
    'stage_weighment': 'वजनकाटा मोजमाप',
    'stage_unloading': 'यार्ड अनलोडिंग',
    'stage_payment': 'DBT पेमेंट सेटलमेंट',
    'stage_completed': 'खरेदी पूर्ण',
    'done': 'पूर्ण',
    'in_progress': 'प्रगतीत',
    'not_done': 'पूर्ण नाही',
    'no_gate_pass': 'कोणतेही सक्रिय गेट पास आढळले नाही.\nपास तयार करण्यासाठी कृपया स्लॉट बुक करा.',
    'profile_info': 'नोंदणीकृत खाते माहिती',
    'land_holding': 'जमीन धारण:',
    'total_stock': 'एकूण साठा:',
    'bank_acc': 'बँक खाते क्र.:',
    'ifsc_code': 'IFSC कोड:',
    'vehicle_plate': 'वाहन प्लेट:',
    'center_label': 'खरेदी केंद्र:',
    'btn_logout': 'ॲपमधून बाहेर पडा',
    'btn_download_receipt': 'अधिकृत DBT पावती डाउनलोड करा',
    'receipt_dialog_title': 'अधिकृत DBT पेमेंट पावती',
    'receipt_dialog_close': 'बंद करा',
    'refresh': 'रिफ्रेश',
    'token_id': 'टोकन आयडी',
    'farmer_name': 'शेतकऱ्याचे नाव',
    'vehicle': 'वाहन'
  }
};

String currentLang = 'en';
String tr(String key) => appTranslations[currentLang]?[key] ?? appTranslations['en']?[key] ?? key;

class FarmerApp extends StatelessWidget {
  const FarmerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KrishiSetu App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: const Color(0xFFF8FAF8),
        primaryColor: const Color(0xFF2E7D32),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E7D32), primary: const Color(0xFF2E7D32)),
        fontFamily: 'Roboto', useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}

// ---------------------------------------------------------
// REUSABLE WIDGETS
// ---------------------------------------------------------
Widget _buildTextField({
  required TextEditingController controller,
  required String label,
  TextInputType type = TextInputType.text,
  int? maxLength,
  TextCapitalization textCapitalization = TextCapitalization.none,
  String? Function(String?)? validator,
}) {
  return TextFormField(
    controller: controller, keyboardType: type, maxLength: maxLength, textCapitalization: textCapitalization,
    decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), counterText: ""),
    validator: validator ?? (val) => (val == null || val.trim().isEmpty) ? "⚠️ Required" : null,
  );
}

// ---------------------------------------------------------
// 1. SPLASH SCREEN
// ---------------------------------------------------------
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const AuthSelectionScreen()),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF337936),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 140,
              height: 140,
              padding: const EdgeInsets.all(12),
              decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
              child: ClipOval(
                child: Image.asset('assets/icon/app_logo.png', fit: BoxFit.contain),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              "KrishiSetu App",
              style: TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.bold, letterSpacing: 0.5),
            ),
            const SizedBox(height: 12),
            const Text(
              "Direct APMC Farmer Procurement Portal",
              style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w400),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 2. AUTH SELECTION SCREEN
// ---------------------------------------------------------
class AuthSelectionScreen extends StatelessWidget {
  const AuthSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF2E7D32),
        title: Text("${tr('select_lang')} / Language", style: const TextStyle(color: Colors.white, fontSize: 16)),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0),
            child: DropdownButton<String>(
              value: currentLang, dropdownColor: const Color(0xFF2E7D32),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold), underline: Container(),
              items: const [DropdownMenuItem(value: 'en', child: Text("English")), DropdownMenuItem(value: 'hi', child: Text("हिन्दी")), DropdownMenuItem(value: 'mr', child: Text("मराठी"))],
              onChanged: (val) {
                if (val != null) {
                  currentLang = val;
                  (context as Element).markNeedsBuild();
                }
              },
            ),
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 400),
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: [BoxShadow(color: Colors.black.withAlpha(10), blurRadius: 15, offset: const Offset(0, 5))]),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.agriculture, size: 55, color: Color(0xFF2E7D32)),
                const SizedBox(height: 12),
                Text(tr('app_title'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                const SizedBox(height: 6),
                Text(tr('tagline'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                const SizedBox(height: 32),
                ElevatedButton.icon(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PhoneLoginScreen())),
                  icon: const Icon(Icons.login), label: Text(tr('btn_login_existing'), style: const TextStyle(fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FarmerRegistrationScreen())),
                  icon: const Icon(Icons.person_add_alt_1), label: Text(tr('btn_create_acc'), style: const TextStyle(fontWeight: FontWeight.bold)),
                  style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF2E7D32), side: const BorderSide(color: Color(0xFF2E7D32), width: 1.5), padding: const EdgeInsets.symmetric(vertical: 16), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 3. PHONE LOGIN SCREEN
// ---------------------------------------------------------
class PhoneLoginScreen extends StatefulWidget { const PhoneLoginScreen({super.key}); @override State<PhoneLoginScreen> createState() => _PhoneLoginScreenState(); }

class _PhoneLoginScreenState extends State<PhoneLoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final phoneCtrl = TextEditingController(text: "9876543210");

  void handleSendOTP() {
    if (_formKey.currentState!.validate()) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => OTPScreen(phoneNumber: phoneCtrl.text.trim(), isRegistrationFlow: false)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('btn_login_existing')), backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 400),
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: [BoxShadow(color: Colors.black.withAlpha(10), blurRadius: 15, offset: const Offset(0, 5))]),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(tr('auth_welcome'), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Text(tr('auth_subtitle'), style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(height: 24),
                  _buildTextField(
                    controller: phoneCtrl, label: tr('lbl_mobile'), type: TextInputType.phone, maxLength: 10,
                    validator: (val) => (val == null || val.trim().length != 10 || !RegExp(r'^[0-9]+$').hasMatch(val.trim())) ? '⚠️ Enter a valid 10-digit mobile number' : null,
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: handleSendOTP,
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                    child: Text(tr('btn_send_otp'), style: const TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 4. NEW FARMER REGISTRATION SCREEN
// ---------------------------------------------------------
class FarmerRegistrationScreen extends StatefulWidget { const FarmerRegistrationScreen({super.key}); @override State<FarmerRegistrationScreen> createState() => _FarmerRegistrationScreenState(); }

class _FarmerRegistrationScreenState extends State<FarmerRegistrationScreen> {
  final _regFormKey = GlobalKey<FormState>();

  final nameCtrl = TextEditingController(text: "Suresh Kumar Verma");
  final phoneCtrl = TextEditingController(text: "9876543210");
  final aadhaarCtrl = TextEditingController(text: "");
  final bankCtrl = TextEditingController(text: "918273645012");
  final ifscCtrl = TextEditingController(text: "SBIN0001234");
  final landCtrl = TextEditingController(text: "6.5");
  final villageCtrl = TextEditingController(text: "Hingna, Nagpur");
  final stockCtrl = TextEditingController(text: "120");
  final weightCtrl = TextEditingController(text: "40");
  final vehicleNoCtrl = TextEditingController(text: "MH-31-TR-9044");
  final vehicleCountCtrl = TextEditingController(text: "1");

  String selectedCrop = "Soybean";
  String selectedSlot = "";
  String selectedVehicleType = "Tractor Trolley";
  
  // Procurement Centers Demo Data
  final List<String> procurementCenters = [
    "Nagpur Central APMC Yard 01",
    "Hingna Sub-Yard 02",
    "Butibori Agro Hub 03"
  ];
  late String selectedProcurementCenter;

  final List<String> cropList = ["Soybean", "Wheat", "Paddy (Rice)", "Cotton"];
  List<Map<String, dynamic>> availableSlots = [];
  bool isLoadingSlots = true;
  bool isHouseFull = false;

  @override
  void initState() {
    super.initState();
    selectedProcurementCenter = procurementCenters.first;
    _fetchAvailableSlots();
  }

  Future<void> _fetchAvailableSlots() async {
    try {
      final res = await http.get(Uri.parse('$kBaseUrl/api/v1/slots/available'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final slots = List<Map<String, dynamic>>.from(data['slots']);
        setState(() {
          availableSlots = slots;
          isHouseFull = slots.isEmpty;
          isLoadingSlots = false;
          if (!isHouseFull) selectedSlot = slots.first['slot'];
        });
      }
    } catch (e) {
      setState(() => isLoadingSlots = false);
    }
  }

  void proceedToOTP() {
    if (isHouseFull) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('house_full_alert')), backgroundColor: Colors.red));
      return;
    }
    if (_regFormKey.currentState!.validate() && selectedSlot.isNotEmpty) {
      final payload = {
        "farmer_name": nameCtrl.text.trim(), "phone_number": phoneCtrl.text.trim(),
        "aadhaar_last_four": aadhaarCtrl.text.trim(), "bank_account_no": bankCtrl.text.trim(),
        "ifsc_code": ifscCtrl.text.trim().toUpperCase(), "land_area_acres": double.tryParse(landCtrl.text.trim()) ?? 0.0,
        "village": villageCtrl.text.trim(), "total_harvest_stock_qtl": double.tryParse(stockCtrl.text.trim()) ?? 0.0,
        "selected_crop": selectedCrop, "weight_to_bring": double.tryParse(weightCtrl.text.trim()) ?? 0.0,
        "vehicle_type": selectedVehicleType, "vehicle_number": "${vehicleNoCtrl.text.trim()} (${vehicleCountCtrl.text.trim()} Veh)",
        "preferred_slot": selectedSlot, "procurement_center": selectedProcurementCenter,
      };
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => OTPScreen(phoneNumber: phoneCtrl.text.trim(), isRegistrationFlow: true, registrationPayload: payload)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('reg_title')), backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _regFormKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(tr('reg_title'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)), const SizedBox(height: 4),
              Text(tr('reg_subtitle'), style: const TextStyle(fontSize: 12, color: Colors.grey)), const SizedBox(height: 16),
              
              _buildTextField(controller: nameCtrl, label: tr('lbl_fullname')), const SizedBox(height: 12),
              _buildTextField(
                controller: phoneCtrl, label: tr('lbl_mobile'), type: TextInputType.phone, maxLength: 10,
                validator: (val) => (val == null || val.trim().length != 10 || !RegExp(r'^[0-9]+$').hasMatch(val.trim())) ? '⚠️ Enter a valid 10-digit mobile number' : null,
              ), const SizedBox(height: 12),
              _buildTextField(
                controller: aadhaarCtrl, label: tr('lbl_aadhaar'), type: TextInputType.number, maxLength: 4,
                validator: (val) => (val == null || val.trim().length != 4 || !RegExp(r'^[0-9]+$').hasMatch(val.trim())) ? '⚠️ Enter exactly 4 digits' : null,
              ), const SizedBox(height: 12),
              _buildTextField(
                controller: bankCtrl, label: tr('lbl_bank'), type: TextInputType.number,
                validator: (val) => (val == null || val.trim().length < 9 || !RegExp(r'^[0-9]+$').hasMatch(val.trim())) ? '⚠️ Enter valid bank account' : null,
              ), const SizedBox(height: 12),
              _buildTextField(controller: ifscCtrl, label: tr('lbl_ifsc'), textCapitalization: TextCapitalization.characters, validator: (val) => (val == null || val.trim().length < 5) ? "⚠️ Enter valid IFSC" : null), const SizedBox(height: 12),
              
              Row(children: [ Expanded(child: _buildTextField(controller: landCtrl, label: tr('lbl_land'), type: TextInputType.number)), const SizedBox(width: 10), Expanded(child: _buildTextField(controller: villageCtrl, label: tr('lbl_village'))) ]), const SizedBox(height: 12),
              
              // Procurement Center Dropdown
              DropdownButtonFormField<String>(
                value: selectedProcurementCenter,
                items: procurementCenters.map((center) => DropdownMenuItem(value: center, child: Text(center, style: const TextStyle(fontSize: 13)))).toList(),
                onChanged: (val) => setState(() => selectedProcurementCenter = val!),
                decoration: InputDecoration(labelText: tr('lbl_procurement_center'), border: const OutlineInputBorder()),
              ), const SizedBox(height: 12),

              _buildTextField(controller: stockCtrl, label: tr('lbl_stock'), type: TextInputType.number), const SizedBox(height: 12),
              
              DropdownButtonFormField<String>(
                initialValue: selectedCrop, items: cropList.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: (val) => setState(() => selectedCrop = val!), decoration: InputDecoration(labelText: tr('lbl_commodity'), border: const OutlineInputBorder()),
              ), const SizedBox(height: 12),
              
              _buildTextField(controller: weightCtrl, label: tr('lbl_weight'), type: TextInputType.number), const SizedBox(height: 12),
              
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: DropdownButtonFormField<String>(
                      initialValue: selectedVehicleType, items: ["Tractor Trolley", "Mini Truck", "Bullock Cart"].map((v) => DropdownMenuItem(value: v, child: Text(v, style: const TextStyle(fontSize: 13)))).toList(),
                      onChanged: (val) => setState(() => selectedVehicleType = val!), decoration: InputDecoration(labelText: tr('lbl_vehicle_type'), border: const OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 1,
                    child: _buildTextField(
                      controller: vehicleCountCtrl, label: tr('lbl_veh_count'), type: TextInputType.number,
                      validator: (val) => (val == null || val.trim().isEmpty || int.tryParse(val.trim()) == null || int.parse(val.trim()) < 1) ? '⚠️ Min 1' : null,
                    ),
                  ),
                ],
              ), const SizedBox(height: 12),
              _buildTextField(controller: vehicleNoCtrl, label: tr('lbl_veh_plate'), textCapitalization: TextCapitalization.characters), const SizedBox(height: 12),
              
              if (isLoadingSlots)
                const Center(child: CircularProgressIndicator())
              else if (isHouseFull)
                Container(padding: const EdgeInsets.all(12), color: Colors.red.shade100, child: Text(tr('house_full_alert'), style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold)))
              else
                DropdownButtonFormField<String>(
                  initialValue: selectedSlot.isNotEmpty ? selectedSlot : null,
                  items: availableSlots.map((s) => DropdownMenuItem(value: s['slot'] as String, child: Text("${s['slot']} (${s['space_left_qtl']} Qtl Space Left)", style: const TextStyle(fontWeight: FontWeight.bold)))).toList(),
                  onChanged: (val) => setState(() => selectedSlot = val!), decoration: InputDecoration(labelText: tr('lbl_target_slot'), border: const OutlineInputBorder()),
                ),

              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: (isHouseFull || isLoadingSlots) ? null : proceedToOTP,
                style: ElevatedButton.styleFrom(backgroundColor: (isHouseFull) ? Colors.grey : const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                child: Text(tr('btn_submit_pass'), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 5. OTP VERIFICATION SCREEN
// ---------------------------------------------------------
class OTPScreen extends StatefulWidget {
  final String phoneNumber; final bool isRegistrationFlow; final Map<String, dynamic>? registrationPayload;
  const OTPScreen({super.key, required this.phoneNumber, required this.isRegistrationFlow, this.registrationPayload});
  @override State<OTPScreen> createState() => _OTPScreenState();
}

class _OTPScreenState extends State<OTPScreen> {
  final _otpFormKey = GlobalKey<FormState>();
  final otpCtrl = TextEditingController(text: "5678");
  bool isLoading = false;

  Future<void> verifyOTP() async {
    if (!_otpFormKey.currentState!.validate()) return;

    setState(() => isLoading = true);

    Map<String, dynamic>? generatedToken;

    if (widget.isRegistrationFlow && widget.registrationPayload != null) {
      final p = widget.registrationPayload!;
      try {
        final regRes = await http.post(
          Uri.parse('$kBaseUrl/api/v1/farmer/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            "farmer_name": p['farmer_name'],
            "phone_number": p['phone_number'],
            "aadhaar_last_four": p['aadhaar_last_four'],
            "bank_account_no": p['bank_account_no'],
            "ifsc_code": p['ifsc_code'],
            "land_area_acres": p['land_area_acres'],
            "village": p['village'],
            "total_harvest_stock_qtl": p['total_harvest_stock_qtl'],
            "procurement_center": p['procurement_center']
          }),
        );

        if (regRes.statusCode == 200) {
          final slotRes = await http.post(
            Uri.parse('$kBaseUrl/api/v1/slots/book'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              "farmer_phone": p['phone_number'],
              "commodity": p['selected_crop'],
              "weight_to_bring_quintals": p['weight_to_bring'],
              "vehicle_type": p['vehicle_type'],
              "vehicle_number": p['vehicle_number'],
              "preferred_slot": p['preferred_slot']
            }),
          );

          if (slotRes.statusCode == 200) {
            generatedToken = jsonDecode(slotRes.body)['token'];
          } else if (mounted) {
            final errData = jsonDecode(slotRes.body);
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(errData['detail'] ?? "⚠️ Booking error occurred"), backgroundColor: Colors.red),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("⚠️ Network Error: Could not connect to backend server."), backgroundColor: Colors.orange),
          );
        }
      }
    }

    setState(() => isLoading = false);

    showLocalNotification("Authentication Success", "Logged in as +91 ${widget.phoneNumber}");

    if (!mounted) return;

    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (_) => MainDashboardScreen(
          farmerPhone: widget.phoneNumber,
          initialToken: generatedToken,
          initialDataPayload: widget.registrationPayload,
        ),
      ),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('otp_title')), backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 400),
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: [BoxShadow(color: Colors.black.withAlpha(10), blurRadius: 15, offset: const Offset(0, 5))]),
            child: Form(
              key: _otpFormKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.mark_email_read, color: Color(0xFF2E7D32), size: 48), const SizedBox(height: 16),
                  Text(tr('otp_title'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)), const SizedBox(height: 8),
                  Text("${tr('otp_subtitle')} ${widget.phoneNumber}", textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: Colors.grey)), const SizedBox(height: 24),
                  _buildTextField(
                    controller: otpCtrl, label: "", type: TextInputType.number, maxLength: 4,
                    validator: (val) => (val == null || val.trim().length != 4) ? '⚠️ Enter valid 4-digit OTP' : null,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: isLoading ? null : verifyOTP,
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                    child: isLoading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Text(tr('btn_verify'), style: const TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 6. MAIN DASHBOARD SCREEN
// ---------------------------------------------------------
class MainDashboardScreen extends StatefulWidget {
  final String farmerPhone; final Map<String, dynamic>? initialToken; final Map<String, dynamic>? initialDataPayload;
  const MainDashboardScreen({super.key, required this.farmerPhone, this.initialToken, this.initialDataPayload});
  @override State<MainDashboardScreen> createState() => _MainDashboardScreenState();
}

class _MainDashboardScreenState extends State<MainDashboardScreen> {
  final _regFormKey = GlobalKey<FormState>();
  int _selectedTab = 0; bool isRegistered = false; Map<String, dynamic>? activeToken;
  Timer? _statusPollTimer; Timer? _queuePollTimer;
  int farmersAheadInQueue = 0; int dynamicWaitMins = 25;

  late TextEditingController phoneCtrl, nameCtrl, aadhaarCtrl, bankCtrl, ifscCtrl, landCtrl, villageCtrl, stockCtrl, weightCtrl, vehicleNoCtrl, vehicleCountCtrl;

  String selectedCrop = "Soybean"; String selectedSlot = ""; String selectedVehicleType = "Tractor Trolley";
  
  final List<String> procurementCenters = [
    "Nagpur Central APMC Yard 01",
    "Hingna Sub-Yard 02",
    "Butibori Agro Hub 03"
  ];
  late String selectedProcurementCenter;

  List<Map<String, dynamic>> availableSlots = [];
  bool isLoadingSlots = true; bool isHouseFull = false;

  final Map<String, double> mspRates = { "Soybean": 4892.00, "Wheat": 2275.00, "Paddy (Rice)": 2300.00, "Cotton": 7121.00 };

  List<Map<String, String>> get stageMaster => [
    {"key": "REQUESTED", "title": tr('stage_requested')}, {"key": "OFFICER_ACCEPTED", "title": tr('stage_accepted')},
    {"key": "GATE_IN", "title": tr('stage_gate_in')}, {"key": "ASSAYING", "title": tr('stage_assaying')},
    {"key": "WEIGHMENT", "title": tr('stage_weighment')}, {"key": "UNLOADING", "title": tr('stage_unloading')},
    {"key": "PAYMENT_PROCESSING", "title": tr('stage_payment')}, {"key": "COMPLETED", "title": tr('stage_completed')},
  ];

  @override
  void initState() {
    super.initState();
    final p = widget.initialDataPayload;
    phoneCtrl = TextEditingController(text: widget.farmerPhone); nameCtrl = TextEditingController(text: p?['farmer_name'] ?? "Suresh Kumar Verma");
    aadhaarCtrl = TextEditingController(text: p?['aadhaar_last_four'] ?? ""); bankCtrl = TextEditingController(text: p?['bank_account_no'] ?? "918273645012");
    ifscCtrl = TextEditingController(text: p?['ifsc_code'] ?? "SBIN0001234"); landCtrl = TextEditingController(text: p?['land_area_acres']?.toString() ?? "6.5");
    villageCtrl = TextEditingController(text: p?['village'] ?? "Hingna, Nagpur"); stockCtrl = TextEditingController(text: p?['total_harvest_stock_qtl']?.toString() ?? "120");
    weightCtrl = TextEditingController(text: p?['weight_to_bring']?.toString() ?? "40"); vehicleNoCtrl = TextEditingController(text: p?['vehicle_number'] ?? "MH-31-TR-9044");
    vehicleCountCtrl = TextEditingController(text: "1");
    selectedProcurementCenter = p?['procurement_center'] ?? procurementCenters.first;

    if (widget.initialToken != null) { activeToken = widget.initialToken; isRegistered = true; _selectedTab = 2; }
    
    _fetchAvailableSlots();
    _startLiveStatusPolling(); _fetchQueuePosition();
  }

  @override
  void dispose() {
    _statusPollTimer?.cancel(); _queuePollTimer?.cancel();
    phoneCtrl.dispose(); nameCtrl.dispose(); aadhaarCtrl.dispose(); bankCtrl.dispose(); ifscCtrl.dispose();
    landCtrl.dispose(); villageCtrl.dispose(); stockCtrl.dispose(); weightCtrl.dispose(); vehicleNoCtrl.dispose(); vehicleCountCtrl.dispose();
    super.dispose();
  }

  Future<void> _fetchAvailableSlots() async {
    try {
      final res = await http.get(Uri.parse('$kBaseUrl/api/v1/slots/available'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final slots = List<Map<String, dynamic>>.from(data['slots']);
        if (mounted) {
          setState(() {
            availableSlots = slots; isHouseFull = slots.isEmpty; isLoadingSlots = false;
            if (!isHouseFull) selectedSlot = slots.first['slot'];
          });
        }
      }
    } catch (_) { if (mounted) setState(() => isLoadingSlots = false); }
  }

  void _startLiveStatusPolling() {
    _statusPollTimer = Timer.periodic(const Duration(seconds: 3), (_) { if (activeToken != null) _fetchLatestTokenStatus(); });
    _queuePollTimer = Timer.periodic(const Duration(seconds: 5), (_) { if (activeToken != null) _fetchQueuePosition(); });
  }

  Future<void> _fetchQueuePosition() async {
    if (activeToken == null || activeToken!['token_id'] == null) return;
    try {
      final res = await http.get(Uri.parse('$kBaseUrl/api/v1/slots/queue-position/${activeToken!['token_id']}'));
      if (res.statusCode == 200 && mounted) {
        final data = jsonDecode(res.body);
        setState(() { farmersAheadInQueue = data['farmers_ahead'] ?? 0; dynamicWaitMins = data['estimated_wait_minutes'] ?? 25; });
      }
    } catch (_) {}
  }

  Future<void> _fetchLatestTokenStatus() async {
    if (activeToken == null || activeToken!['token_id'] == null) return;
    try {
      final res = await http.get(Uri.parse('$kBaseUrl/api/v1/slots/status/${activeToken!['token_id']}'));
      if (res.statusCode == 200 && mounted) {
        final data = jsonDecode(res.body);
        Map<String, dynamic> tk = data.containsKey('token') ? data['token'] : data;
        String oldOfficerStatus = activeToken!['officer_status'] ?? 'PENDING_APPROVAL';
        String newOfficerStatus = tk['officer_status'] ?? tk['status'] ?? oldOfficerStatus;
        String oldStage = activeToken!['current_stage'] ?? 'REQUESTED';
        String newStage = tk['current_stage'] ?? oldStage;

        if (oldOfficerStatus != newOfficerStatus || oldStage != newStage) {
          setState(() { activeToken!['officer_status'] = newOfficerStatus; activeToken!['current_stage'] = newStage; });
          showLocalNotification("🚜 APMC Mandi Status Update", "Status: $newOfficerStatus | Yard Stage: $newStage");
        }
      }
    } catch (_) {}
  }

  Future<void> registerAndBookSlot() async {
    if (isHouseFull) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('house_full_alert')), backgroundColor: Colors.red)); return; }
    if (!_regFormKey.currentState!.validate() || selectedSlot.isEmpty) return;

    try {
      final regRes = await http.post(
        Uri.parse('$kBaseUrl/api/v1/farmer/register'), headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          "farmer_name": nameCtrl.text.trim(), "phone_number": phoneCtrl.text.trim(), "aadhaar_last_four": aadhaarCtrl.text.trim(),
          "bank_account_no": bankCtrl.text.trim(), "ifsc_code": ifscCtrl.text.trim().toUpperCase(), "land_area_acres": double.tryParse(landCtrl.text.trim()) ?? 0.0,
          "village": villageCtrl.text.trim(), "total_harvest_stock_qtl": double.tryParse(stockCtrl.text.trim()) ?? 0.0,
          "procurement_center": selectedProcurementCenter
        }),
      );
      if (regRes.statusCode == 200) {
        setState(() => isRegistered = true);
        final slotRes = await http.post(
          Uri.parse('$kBaseUrl/api/v1/slots/book'), headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            "farmer_phone": phoneCtrl.text.trim(), "commodity": selectedCrop, "weight_to_bring_quintals": double.tryParse(weightCtrl.text.trim()) ?? 0.0,
            "vehicle_type": selectedVehicleType, "vehicle_number": "${vehicleNoCtrl.text.trim()} (${vehicleCountCtrl.text.trim()} Veh)", "preferred_slot": selectedSlot
          }),
        );
        final data = jsonDecode(slotRes.body);
        if (slotRes.statusCode == 200) {
          setState(() { activeToken = data["token"]; _selectedTab = 2; });
          showLocalNotification("Slot Request Sent 📋", "Token sent to Procurement Officer for approval.");
        } else {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(data['detail'] ?? "⚠️ Error"), backgroundColor: Colors.red));
        }
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("⚠️ Network Error")));
    }
  }

  Future<void> _downloadReceipt(String tokenId) async {
    try {
      final url = Uri.parse('$kBaseUrl/api/v1/downloads/farmer/receipt/$tokenId?phone=${phoneCtrl.text.trim()}');
      final res = await http.get(url);
      if (res.statusCode == 200) {
        final receiptText = res.body;
        if (!mounted) return;
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(tr('receipt_dialog_title')),
            content: SizedBox(
              width: double.maxFinite,
              child: SingleChildScrollView(
                child: SelectableText(
                  receiptText,
                  style: const TextStyle(fontFamily: 'Courier', fontSize: 12),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: Text(tr('receipt_dialog_close')),
              ),
            ],
          ),
        );
      } else {
        final errData = jsonDecode(res.body);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errData['detail'] ?? "⚠️ Could not download receipt"), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("⚠️ Network Error downloading receipt"), backgroundColor: Colors.orange),
      );
    }
  }

  int _getStageIndex(String stageKey) { 
    final stages = stageMaster;
    for (int i = 0; i < stages.length; i++) { if (stages[i]["key"] == stageKey) return i; } 
    return 0; 
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        elevation: 0, backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white,
        title: Row(children: [const Icon(Icons.agriculture, color: Colors.white), const SizedBox(width: 8), Text(tr('app_title'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18))]),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0),
            child: DropdownButton<String>(
              value: currentLang, dropdownColor: const Color(0xFF2E7D32),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold), underline: Container(),
              items: const [DropdownMenuItem(value: 'en', child: Text("EN")), DropdownMenuItem(value: 'hi', child: Text("हिंदी")), DropdownMenuItem(value: 'mr', child: Text("मराठी"))],
              onChanged: (val) { if (val != null) setState(() => currentLang = val); },
            ),
          ),
          IconButton(icon: const Icon(Icons.account_circle, size: 28), onPressed: () => setState(() => _selectedTab = 3)), const SizedBox(width: 8),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            if (_selectedTab == 0) _buildCropPricesTab(), if (_selectedTab == 1) _buildRegistrationTab(),
            if (_selectedTab == 2) _buildGatePassTab(), if (_selectedTab == 3) _buildCustomerProfileTab(),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedTab, selectedItemColor: const Color(0xFF2E7D32), unselectedItemColor: Colors.grey, type: BottomNavigationBarType.fixed,
        onTap: (index) { setState(() => _selectedTab = index); if (index == 2 && activeToken != null) { _fetchLatestTokenStatus(); _fetchQueuePosition(); } },
        items: [
          BottomNavigationBarItem(icon: const Icon(Icons.eco), label: tr('tab_rates')), BottomNavigationBarItem(icon: const Icon(Icons.edit_calendar), label: tr('tab_book')),
          BottomNavigationBarItem(icon: const Icon(Icons.qr_code_2), label: tr('tab_pass')), BottomNavigationBarItem(icon: const Icon(Icons.person), label: tr('tab_profile')),
        ],
      ),
    );
  }

  Widget _buildCropPricesTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: const Color(0xFFE8F5E9), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFC8E6C9))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text("${tr('welcome_farmer')} ${nameCtrl.text.isNotEmpty ? nameCtrl.text : 'Farmer'}!", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
            const SizedBox(height: 4), Text(tr('msp_subtitle'), style: const TextStyle(fontSize: 12, color: Colors.black87)),
          ]),
        ),
        const SizedBox(height: 20), Text(tr('msp_header'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)), const SizedBox(height: 12),
        ...mspRates.entries.map((e) => Card(
          elevation: 1, margin: const EdgeInsets.only(bottom: 10), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          child: ListTile(
            leading: const CircleAvatar(backgroundColor: Color(0xFFE8F5E9), child: Icon(Icons.grass, color: Color(0xFF2E7D32))),
            title: Text(e.key, style: const TextStyle(fontWeight: FontWeight.bold)), subtitle: Text(tr('gov_guarantee')),
            trailing: Text("₹${e.value.toStringAsFixed(0)} / Qtl", style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF2E7D32), fontSize: 15)),
          ),
        )),
        const SizedBox(height: 16),
        ElevatedButton(
          onPressed: () => setState(() => _selectedTab = 1),
          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
          child: Text(tr('btn_book_now'), style: const TextStyle(fontWeight: FontWeight.bold)),
        )
      ],
    );
  }

  Widget _buildRegistrationTab() {
    return Container(
      padding: const EdgeInsets.all(20), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
      child: Form(
        key: _regFormKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(tr('reg_title'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)), const SizedBox(height: 4),
            Text(tr('reg_subtitle'), style: const TextStyle(fontSize: 12, color: Colors.grey)), const SizedBox(height: 16),
            
            _buildTextField(controller: nameCtrl, label: tr('lbl_fullname')), const SizedBox(height: 12),
            _buildTextField(
              controller: phoneCtrl, label: tr('lbl_mobile'), type: TextInputType.phone, maxLength: 10,
              validator: (val) => (val == null || val.trim().length != 10) ? '⚠️ Valid 10 digits required' : null,
            ), const SizedBox(height: 12),
            _buildTextField(
              controller: aadhaarCtrl, label: tr('lbl_aadhaar'), type: TextInputType.number, maxLength: 4,
              validator: (val) => (val == null || val.trim().length != 4) ? '⚠️ Enter last 4 digits' : null,
            ), const SizedBox(height: 12),
            _buildTextField(controller: bankCtrl, label: tr('lbl_bank'), type: TextInputType.number), const SizedBox(height: 12),
            _buildTextField(controller: ifscCtrl, label: tr('lbl_ifsc'), textCapitalization: TextCapitalization.characters), const SizedBox(height: 12),
            
            Row(children: [ Expanded(child: _buildTextField(controller: landCtrl, label: tr('lbl_land'), type: TextInputType.number)), const SizedBox(width: 10), Expanded(child: _buildTextField(controller: villageCtrl, label: tr('lbl_village'))) ]), const SizedBox(height: 12),
            
            // Procurement Center Dropdown
            DropdownButtonFormField<String>(
              value: selectedProcurementCenter,
              items: procurementCenters.map((center) => DropdownMenuItem(value: center, child: Text(center, style: const TextStyle(fontSize: 13)))).toList(),
              onChanged: (val) => setState(() => selectedProcurementCenter = val!),
              decoration: InputDecoration(labelText: tr('lbl_procurement_center'), border: const OutlineInputBorder()),
            ), const SizedBox(height: 12),

            _buildTextField(controller: stockCtrl, label: tr('lbl_stock'), type: TextInputType.number), const SizedBox(height: 12),
            
            DropdownButtonFormField<String>(
              initialValue: selectedCrop, items: mspRates.keys.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
              onChanged: (val) => setState(() => selectedCrop = val!), decoration: InputDecoration(labelText: tr('lbl_commodity'), border: const OutlineInputBorder()),
            ), const SizedBox(height: 12),
            
            _buildTextField(controller: weightCtrl, label: tr('lbl_weight'), type: TextInputType.number), const SizedBox(height: 12),
            
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: DropdownButtonFormField<String>(
                    initialValue: selectedVehicleType, items: ["Tractor Trolley", "Mini Truck", "Bullock Cart"].map((v) => DropdownMenuItem(value: v, child: Text(v, style: const TextStyle(fontSize: 13)))).toList(),
                    onChanged: (val) => setState(() => selectedVehicleType = val!), decoration: InputDecoration(labelText: tr('lbl_vehicle_type'), border: const OutlineInputBorder()),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(flex: 1, child: _buildTextField(controller: vehicleCountCtrl, label: tr('lbl_veh_count'), type: TextInputType.number)),
              ],
            ), const SizedBox(height: 12),
            _buildTextField(controller: vehicleNoCtrl, label: tr('lbl_veh_plate'), textCapitalization: TextCapitalization.characters), const SizedBox(height: 12),
            
            if (isLoadingSlots)
              const Center(child: CircularProgressIndicator())
            else if (isHouseFull)
              Container(padding: const EdgeInsets.all(12), color: Colors.red.shade100, child: Text(tr('house_full_alert'), style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold)))
            else
              DropdownButtonFormField<String>(
                initialValue: selectedSlot.isNotEmpty ? selectedSlot : null,
                items: availableSlots.map((s) => DropdownMenuItem(value: s['slot'] as String, child: Text("${s['slot']} (${s['space_left_qtl']} Qtl Space Left)", style: const TextStyle(fontWeight: FontWeight.bold)))).toList(),
                onChanged: (val) => setState(() => selectedSlot = val!), decoration: InputDecoration(labelText: tr('lbl_target_slot'), border: const OutlineInputBorder()),
              ),

            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: (isHouseFull || isLoadingSlots) ? null : registerAndBookSlot,
              style: ElevatedButton.styleFrom(backgroundColor: (isHouseFull) ? Colors.grey : const Color(0xFF2E7D32), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
              child: Text(tr('btn_submit_pass'), style: const TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGatePassTab() {
    String currentStage = activeToken?['current_stage'] ?? "REQUESTED";
    String officerStatus = activeToken?['officer_status'] ?? activeToken?['status'] ?? "PENDING_APPROVAL";
    int currentStageIdx = _getStageIndex(currentStage);
    bool isApproved = officerStatus == 'ACCEPTED' || officerStatus == 'APPROVED';
    bool isRejected = officerStatus == 'REJECTED';
    bool isCompleted = currentStage == 'COMPLETED';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(tr('tab_pass'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            IconButton(icon: const Icon(Icons.refresh, color: Color(0xFF2E7D32)), onPressed: () { _fetchLatestTokenStatus(); _fetchQueuePosition(); }),
          ],
        ),
        const SizedBox(height: 8),
        if (activeToken != null) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(gradient: const LinearGradient(colors: [Color(0xFF2E7D32), Color(0xFF4CAF50)]), borderRadius: BorderRadius.circular(12), boxShadow: [BoxShadow(color: Colors.black.withAlpha(20), blurRadius: 8, offset: const Offset(0, 3))]),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(tr('live_queue'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)), const Icon(Icons.access_time_filled, color: Colors.white70)]),
                const Divider(color: Colors.white24, height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Column(children: [Text(tr('farmers_ahead'), style: const TextStyle(color: Colors.white70, fontSize: 11)), const SizedBox(height: 4), Text("$farmersAheadInQueue", style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold))]),
                    Container(height: 30, width: 1, color: Colors.white30),
                    Column(children: [Text(tr('est_wait'), style: const TextStyle(color: Colors.white70, fontSize: 11)), const SizedBox(height: 4), Text("~ $dynamicWaitMins Mins", style: const TextStyle(color: Colors.amberAccent, fontSize: 22, fontWeight: FontWeight.bold))]),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16), width: double.infinity,
            decoration: BoxDecoration(color: isRejected ? Colors.red[50] : (isApproved ? Colors.green[50] : Colors.orange[50]), border: Border.all(color: isRejected ? Colors.red : (isApproved ? Colors.green : Colors.orange)), borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                Icon(isRejected ? Icons.cancel : (isApproved ? Icons.check_circle : Icons.hourglass_top), color: isRejected ? Colors.red : (isApproved ? Colors.green : Colors.orange), size: 32),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(isRejected ? tr('status_rejected') : (isApproved ? tr('status_approved') : tr('status_pending')), style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: isRejected ? Colors.red[900] : (isApproved ? Colors.green[900] : Colors.orange[900]))),
                      const SizedBox(height: 2),
                      Text(isRejected ? tr('status_rejected_desc') : (isApproved ? tr('status_approved_desc') : tr('status_pending_desc')), style: const TextStyle(fontSize: 12, color: Colors.black87)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
            child: Column(
              children: [
                Text("${tr('token_id')}: ${activeToken!['token_id']}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))), const SizedBox(height: 4),
                Text("${tr('farmer_name')}: ${activeToken!['farmer_name'] ?? nameCtrl.text}", style: const TextStyle(fontWeight: FontWeight.w600)), const SizedBox(height: 4),
                Text("${tr('vehicle')}: ${activeToken!['vehicle_number'] ?? vehicleNoCtrl.text}", style: const TextStyle(fontSize: 12, color: Colors.black54)), const Divider(height: 24),
                isCompleted ? Text(tr('token_scanned'), style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 13)) : QrImageView(data: activeToken!['token_id'] ?? 'EMPTY', size: 140),
                if (isCompleted || currentStage == 'PAYMENT_PROCESSING') ...[
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => _downloadReceipt(activeToken!['token_id']),
                    icon: const Icon(Icons.download),
                    label: Text(tr('btn_download_receipt')),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20), Text(tr('live_stage_prog'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)), const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
            child: Column(
              children: List.generate(stageMaster.length, (index) {
                String stageTitle = stageMaster[index]["title"]!;
                bool isCompletedStage = index < currentStageIdx || currentStage == "COMPLETED";
                bool isCurrent = index == currentStageIdx && currentStage != "COMPLETED";
                bool isPending = index > currentStageIdx;
                Color circleColor = isCompletedStage ? Colors.green : (isCurrent ? const Color(0xFF2E7D32) : Colors.grey.shade300);
                IconData stepIcon = isCompletedStage ? Icons.check : (isCurrent ? Icons.play_arrow : Icons.circle);

                return Column(
                  children: [
                    Row(
                      children: [
                        CircleAvatar(radius: 13, backgroundColor: circleColor, child: Icon(stepIcon, color: Colors.white, size: 13)), const SizedBox(width: 12),
                        Expanded(child: Text(stageTitle, style: TextStyle(fontWeight: isCurrent || isCompletedStage ? FontWeight.bold : FontWeight.normal, color: isPending ? Colors.grey : Colors.black87, fontSize: 13))),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(color: isCompletedStage ? Colors.green[50] : (isCurrent ? Colors.blue[50] : Colors.grey[100]), borderRadius: BorderRadius.circular(4)),
                          child: Text(isCompletedStage ? tr('done') : (isCurrent ? tr('in_progress') : tr('not_done')), style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: isCompletedStage ? Colors.green[800] : (isCurrent ? Colors.blue[800] : Colors.grey[600]))),
                        ),
                      ],
                    ),
                    if (index < stageMaster.length - 1) Container(margin: const EdgeInsets.only(left: 12), height: 18, width: 2, color: isCompletedStage ? Colors.green : Colors.grey.shade300),
                  ],
                );
              }),
            ),
          ),
        ] else
          Center(child: Padding(padding: const EdgeInsets.all(30.0), child: Text(tr('no_gate_pass'), textAlign: TextAlign.center))),
      ],
    );
  }

  Widget _buildCustomerProfileTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(20), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
          child: Column(
            children: [
              const CircleAvatar(radius: 36, backgroundColor: Color(0xFF2E7D32), child: Icon(Icons.person, size: 45, color: Colors.white)), const SizedBox(height: 12),
              Text(nameCtrl.text.isNotEmpty ? nameCtrl.text : "Farmer Profile", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)), const SizedBox(height: 4),
              Text("Mobile: +91 ${phoneCtrl.text}", style: const TextStyle(color: Colors.black54)), Text("Location: ${villageCtrl.text}", style: const TextStyle(color: Colors.black54)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(tr('profile_info'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)), const Divider(height: 20),
              _buildProfileRow(tr('land_holding'), "${landCtrl.text} Acres"), _buildProfileRow(tr('total_stock'), "${stockCtrl.text} Qtl"),
              _buildProfileRow(tr('center_label'), selectedProcurementCenter),
              _buildProfileRow(tr('bank_acc'), bankCtrl.text), _buildProfileRow(tr('ifsc_code'), ifscCtrl.text),
              _buildProfileRow(tr('lbl_commodity'), selectedCrop), _buildProfileRow(tr('vehicle_plate'), vehicleNoCtrl.text),
            ],
          ),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () => Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const AuthSelectionScreen())),
          icon: const Icon(Icons.logout, color: Colors.red), label: Text(tr('btn_logout'), style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.red), padding: const EdgeInsets.symmetric(vertical: 14)),
        ),
      ],
    );
  }

  Widget _buildProfileRow(String title, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(title, style: const TextStyle(color: Colors.black54, fontSize: 12)), Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12))]),
    );
  }
}