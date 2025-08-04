# CHANGELOG & ROADMAP

## Our Values

This project exists because we believe:
- **Privacy is a human right** - Your words belong to you
- **Technology should unite, not divide** - Breaking language barriers
- **Communities > Corporations** - Local-first, always
- **Accessibility is non-negotiable** - Tech for all
- **Sustainability matters** - Efficient code, low resource use

---

## Changelog

### 2025-08-04 - Major Privacy-First Refactor
- Complete architectural overhaul to privacy-first design
- Removed all WSL-specific and terminal-only code
- Removed legacy meetings directory structure
- Added comprehensive privacy-focused README
- Added capacity.eco mission statement and use cases
- Repositioned project for community organizing and indigenous solidarity
- Enhanced documentation with security and privacy sections
- Added Docker-based deployment architecture
- Implemented WebSocket server (localhost:8765) for browser communication
- Added web UI framework (localhost:8080)

### 2025-08-01 - MS Teams Integration Fix
- Fixed Firefox extension MS Teams CKEditor integration
- Improved chat input detection for Teams platform
- Enhanced browser extension compatibility

### 2025-08-01 - LibreTranslate Support
- Added LibreTranslate as primary translation option
- Implemented self-hosted translation capability
- Added privacy-preserving translation alternative to Google Translate
- Created fallback system for translation services

### 2025-07-31 - Meeting Transcription Tools
- Added Firefox browser extension for meeting integration
- Implemented system audio capture for meeting recording
- Added WebSocket server for real-time browser communication
- Created floating widget UI for transcription display
- Added support for Google Meet and Microsoft Teams
- Implemented auto-insert functionality for meeting chat

### 2025-07-31 - Initial Commit
- Created WSL2 audio recording system
- Implemented Whisper AI integration for transcription
- Added bilingual support (English ↔ Portuguese)
- Created basic Google Translate integration
- Implemented continuous recording with VAD (Voice Activity Detection)

---

## TODO - Short Term

### Critical Security Fixes

- [x] WebSocket Authentication - CRITICAL SECURITY ISSUE - COMPLETED 2025-08-04
  - [x] Currently anyone with ws://address:8765 can listen to all transcriptions
  - [x] move all to localhost or docker internal network
  - [x] updated web ui to connect to docker internal network, not localhost

- [x] Fix Teams CKEditor integration - COMPLETED 2025-08-01
- [ ] Fix hallucination detection for legitimate repetitions
  - [ ] Add context-aware detection
  - [ ] Make sensitivity configurable per model
  - [ ] Add user-controlled thresholds
  - [ ] Whitelist common repeated phrases

- [x] Create Docker Compose setup - COMPLETED 2025-08-04
- [ ] Simplify startup process
  - [ ] Create single startup script for all services
  - [ ] Add web-based control panel
  - [ ] Auto-start transcription when audio clients connect

- [x] Fix WebSocket communication - COMPLETED 2025-08-01
- [ ] Fix WebSocket reconnection after network interruption
- [ ] Fix memory leak in sessions longer than 4 hours
- [ ] Handle audio queue overflow with 3+ devices

- [ ] More authentication allowing possible web hosting or on a local network
  - [ ] Implement JWT token authentication for WebSocket connections
  - [ ] Add session-based access control
  - [ ] Rate limiting to prevent abuse
  - [ ] Optional encryption for WebSocket messages

### Platform Support

- [x] Windows audio support - COMPLETED (enhanced Windows audio client)
- [ ] Linux audio support
  - [ ] PulseAudio client implementation
  - [ ] ALSA fallback option
  - [ ] Installation script for Ubuntu/Debian

- [ ] macOS audio support
  - [ ] Core Audio client implementation
  - [ ] Permissions handling guide

- [ ] Telegram web support
- [ ] Jitsi Meet integration
  - [ ] WebRTC audio stream capture
  - [ ] Participant identification
  - [ ] IFrame API integration

### Other
- [ ] any language <> any language easily switchable (eg EN <> RU)

### Completed Features from Original TODO

- [x] Multi-source audio capture - COMPLETED
  - [x] Windows system audio capture
  - [x] Separate microphone capture with auto-gain
  - [x] Simultaneous capture from multiple sources

- [x] Real-time transcription - COMPLETED
  - [x] Whisper AI integration (local processing)
  - [x] GPU acceleration support
  - [x] Multiple model size options

- [x] Translation system - COMPLETED 2025-08-01
  - [x] LibreTranslate integration (self-hosted)
  - [x] Google Translate fallback
  - [x] Automatic language detection

- [x] WebSocket server - COMPLETED 2025-07-31
  - [x] Real-time communication with browser
  - [x] Reconnection handling
  - [x] Message queuing

- [x] Browser extension - COMPLETED 2025-07-31
  - [x] Firefox/Chrome extension base
  - [x] WebSocket client
  - [x] Floating widget UI
  - [x] Meeting platform detection
  - [x] Google Meet integration
  - [x] Microsoft Teams integration
  - [x] Copy to clipboard
  - [x] Auto-insert to chat

---

## TODO - Medium Term

### Browser Extension

- [ ] Add platform support:
  - [ ] Zoom web client
  - [ ] BigBlueButton
  - [ ] Element/Matrix calls
- [ ] Add keyboard shortcuts for common actions
- [ ] Implement local encrypted storage for preferences

### Audio Processing

- [ ] Implement noise reduction for noisy environments
- [ ] Add speaker diarization for meeting minutes
- [ ] Create intelligent multi-stream mixing
- [ ] Add automatic gain normalization across sources

### UI/UX Improvements

- [ ] Real-time audio level visualization in web UI
- [ ] Full accessibility compliance (WCAG 2.1)
- [ ] Mobile responsive design
- [ ] Dark mode support
- [ ] Localization for UI (starting with PT, ES)

### Collaborative Features

- [ ] Real-time collaborative transcript editing
  - [ ] WebSocket-based synchronized editing
  - [ ] Conflict resolution for simultaneous edits
  - [ ] User attribution and edit history
- [ ] Multiple transcriber support with role-based permissions
- [ ] Consensus-based validation for disputed sections

### Documentation

- [ ] "5 Minute Quick Start" video tutorial
- [ ] "Organizing Multilingual Meetings" guide
- [ ] "Protecting Your Transcripts" security guide
- [ ] Architecture diagrams
- [ ] API documentation
- [ ] Contributing guidelines

---

## TODO - Long Term

### Performance Optimization

- [ ] Integrate faster-whisper for 2x speed improvement
- [ ] Implement streaming/chunked processing
- [ ] Progressive refinement (start with tiny model, upgrade to large)
- [ ] Optimize for low-resource devices (Raspberry Pi)

### Privacy & Security Features

- [ ] Audio scrubbing system
  - [ ] Automatic PII detection and removal
  - [ ] Pre-transcription voice anonymization
  - [ ] Configurable redaction levels
  - [ ] Audit log of scrubbed content
- [ ] Local encryption at rest
- [ ] Secure deletion with overwrite
- [ ] End-to-end encryption for shared transcripts

### Advanced Features

- [ ] Automated meeting summaries with privacy controls
- [ ] Action items extraction
- [ ] Offline-only mode for maximum security
- [ ] Federated transcription network for distributed processing
- [ ] Plugin system for custom extensions

### Alternative Models & Research

- [ ] Evaluate SpeechBrain as fully open source alternative
- [ ] Test Wav2vec2 for specific language support
- [ ] Support community-trained models
- [ ] Indigenous language model training toolkit

### Platform Expansion

- [ ] Native mobile apps (Android/iOS)
- [ ] Desktop applications with system tray
- [ ] Self-contained hardware device (meeting recorder)
- [ ] Integration with more privacy-first platforms

---

## Known Issues

### Critical Bugs
- WebSocket reconnection fails after network interruption
- Memory leak in 4+ hour sessions  
- Audio queue overflow with 3+ simultaneous devices

### Important Bugs
- Whisper hangs on corrupted audio chunks
- Translation fails silently when LibreTranslate is down
- Docker volume permissions incorrect on Linux
- Timestamps drift in recordings over 2 hours

### Minor Bugs
- UI doesn't update when changing languages mid-session
- Special characters break transcript formatting
- Browser extension position resets on page reload

---

## Project Status Summary

### What's Working Now
- ✅ Windows audio capture (system + microphone)
- ✅ Real-time transcription with Whisper
- ✅ LibreTranslate integration for privacy
- ✅ Browser extension for Google Meet & MS Teams
- ✅ WebSocket communication
- ✅ Docker containerization
- ✅ Auto-gain control for microphone
- ✅ Voice Activity Detection (VAD)
- ✅ Multi-language support (EN ↔ PT)

### What Needs Work
- ❌ Cross-platform audio (Linux/Mac)
- ❌ Simplified startup process
- ❌ Hallucination detection accuracy
- ❌ Long session stability
- ❌ Jitsi Meet integration
- ❌ Collaborative editing features

---

## How to Contribute

1. Check the Short Term TODO for immediate needs
2. Review Known Issues for bugs to fix
3. Submit PRs with clear descriptions
4. Focus on privacy-preserving implementations

Special focus areas for capacity.eco:
- Indigenous language support
- Privacy-preserving features
- Collaborative tools for community organizing
- Integration with privacy-first platforms

---

*Built with ❤️ and rage against surveillance capitalism*