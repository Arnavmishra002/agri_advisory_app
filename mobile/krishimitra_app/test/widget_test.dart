import 'package:flutter_test/flutter_test.dart';
import 'package:krishimitra_app/main.dart';

void main() {
  testWidgets('KrishiMitra smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const KrishiMitraApp());
    // Splash screen should show app name
    await tester.pump();
    expect(find.text('KrishiMitra AI'), findsAtLeastNWidgets(1));
  });
}
