# Comprehensive Test Writing Plan for Backend Subapps

## Overview
Write comprehensive tests for each subapp (ai, alerts, core, journey, users) to ensure `python manage.py test` runs all tests successfully. Tests include model tests, serializer tests, and API view tests.

## Apps to Test
- [ ] ai
- [ ] alerts
- [ ] core
- [ ] journey
- [ ] users

## Test Structure per App
For each app, create/update tests.py with:
- ModelTestCase: Test model creation, validation, methods, __str__
- SerializerTestCase: Test serialization, validation, edge cases
- ViewTestCase: Test API endpoints, permissions, responses using APITestCase

## Steps
1. [ ] Write ai/tests.py
   - [ ] VoiceDetectionEvent model tests
   - [ ] AIChatSession model tests
   - [ ] AIChatMessage model tests
   - [ ] MotionDetectionEvent model tests
   - [ ] AIFeedback model tests
   - [ ] Serializer tests for all serializers
   - [ ] View tests for all API endpoints (trigger_voice_detection, trigger_motion_detection, chat sessions, feedback, etc.)

2. [ ] Write alerts/tests.py
   - [ ] Alert model tests
   - [ ] AlertNotification model tests
   - [ ] SafetyNetworkMember model tests
   - [ ] WebSocketConnection model tests
   - [ ] PanicButtonPress model tests
   - [ ] Serializer tests
   - [ ] View tests for alert creation, panic button, safety network, websocket

3. [ ] Write core/tests.py
   - [ ] Minimal tests since models are empty

4. [ ] Write journey/tests.py
   - [ ] Journey model tests (including save method, generate_journey_code)
   - [ ] JourneyLocation model tests
   - [ ] GroupJourney model tests
   - [ ] Passenger model tests
   - [ ] JourneyAlert model tests
   - [ ] Serializer tests
   - [ ] View tests (need to read views.py first)

5. [ ] Write users/tests.py
   - [ ] User model tests (CustomUserManager, creation, authentication)
   - [ ] UserSession model tests
   - [ ] EmergencyContact model tests
   - [ ] Serializer tests
   - [ ] View tests (need to read views.py first)

6. [ ] Run `python manage.py test` to verify all tests pass
7. [ ] Check test coverage and add missing tests if needed
8. [ ] Ensure no import errors or missing dependencies

## Dependencies
- Use Django's TestCase and APITestCase
- Create test users, journeys, etc. using factories or setUp methods
- Mock external services if needed (e.g., AI services, notifications)
- Ensure permissions are tested (IsAuthenticated, etc.)

## Completion Criteria
- All tests pass with `python manage.py test`
- Comprehensive coverage of models, serializers, views
- Tests are isolated and repeatable
