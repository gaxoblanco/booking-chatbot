# WhatsApp Booking Bot

A conversational booking system for healthcare centers, running on WhatsApp.
Patients find professionals, book appointments, and get reminders — no app to download.
Professionals manage everything through Google Calendar as usual.

In production with real clients since November 2025.

## Why no LLM

Connecting an LLM meant a fixed cost per token, multiplied by every message 
from every patient across every health center. Doesn't scale.

Trained a custom spaCy NLU classifier from scratch instead: ~1,050 synthetic examples,
custom data augmentation pipeline, 98.1% accuracy. Runs on the server.
No variable cost. No external dependency for inference.

## Multi-tenant architecture

The ML service runs in a dedicated Docker container, independent from the bot.
Multiple bot instances share the same model simultaneously — each core container 
stays lightweight. New clients onboard without touching the ML infrastructure.

## Stack

Python 3.10 · Flask · spaCy 3.7.2 · Twilio WhatsApp API  
Google Calendar API (Service Account) · Redis · SQLite · Docker

## Key features

- Real-time availability via Google Calendar sync
- Waiting list — canceled slots offered automatically to queued patients
- Appointment reminders with confirmation/cancellation handling
- Tone system — same codebase, different voice per tenant via environment variable
- Session state via Redis (TTL 30 min) with in-memory fallback
- Sliding-window rate limiter and anti-spam controls

## ML details

- Framework: spaCy 3.7.2 with TextCatEnsemble
- Dataset: ~1,050 synthetic examples with custom augmentation pipeline
- Accuracy: 98.1%
- Logic: ML-primary with rule-based fallback for edge cases