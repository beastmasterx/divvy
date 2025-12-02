// Tests for session model.

import 'package:test/test.dart';
import 'package:cli/src/models/session.dart';

void main() {
  group('Session', () {
    test('initializes with default values', () {
      final session = Session();
      expect(session.currentGroupId, isNull);
      expect(session.currentGroupName, isNull);
      expect(session.currentPeriodId, isNull);
      expect(session.currentPeriodName, isNull);
      expect(session.isAuthenticated, isFalse);
    });

    test('setGroup updates group and clears period', () {
      final session = Session();
      session.setGroup(1, 'Test Group');
      
      expect(session.currentGroupId, 1);
      expect(session.currentGroupName, 'Test Group');
      expect(session.currentPeriodId, isNull);
      expect(session.currentPeriodName, isNull);
    });

    test('setPeriod updates period', () {
      final session = Session();
      session.setPeriod(5, 'Test Period');
      
      expect(session.currentPeriodId, 5);
      expect(session.currentPeriodName, 'Test Period');
    });

    test('setGroup clears period when group changes', () {
      final session = Session();
      session.setPeriod(5, 'Period 1');
      session.setGroup(1, 'Group 1');
      
      expect(session.currentGroupId, 1);
      expect(session.currentPeriodId, isNull); // Cleared
    });

    test('clear resets all fields', () {
      final session = Session();
      session.setGroup(1, 'Group');
      session.setPeriod(5, 'Period');
      session.isAuthenticated = true;
      
      session.clear();
      
      expect(session.currentGroupId, isNull);
      expect(session.currentGroupName, isNull);
      expect(session.currentPeriodId, isNull);
      expect(session.currentPeriodName, isNull);
      expect(session.isAuthenticated, isFalse);
    });
  });
}

