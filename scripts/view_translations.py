#!/usr/bin/env python3
# view_translations.py - View LibreTranslate translation logs

import json
import sys
from datetime import datetime

def view_translation_logs(log_file='/app/translations/libretranslate_log.json', last_n=10):
    """View translation logs"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        print(f"\n📋 Translation Log Viewer")
        print(f"   Total entries: {len(logs)}")
        print(f"   Showing last {last_n} entries\n")
        print("=" * 100)
        
        # Get last N entries
        recent_logs = logs[-last_n:] if len(logs) > last_n else logs
        
        for i, entry in enumerate(recent_logs, 1):
            print(f"\n📝 Entry {i}/{len(recent_logs)}")
            print(f"   Request ID: {entry.get('request_id', 'N/A')}")
            print(f"   Timestamp: {entry.get('timestamp', 'N/A')}")
            print(f"   Success: {'✅' if entry.get('success', False) else '❌'}")
            print(f"   Languages: {entry.get('source_lang', 'N/A')} → {entry.get('target_lang', 'N/A')}")
            
            if entry.get('detected_language'):
                detected = entry['detected_language']
                print(f"   Detected: {detected.get('language', 'N/A')} "
                      f"(confidence: {detected.get('confidence', 'N/A')})")
            
            print(f"   Response time: {entry.get('response_time', 'N/A'):.2f}s" 
                  if entry.get('response_time') else "   Response time: N/A")
            
            print(f"\n   Original text ({len(entry.get('original_text', ''))} chars):")
            print(f"   {entry.get('original_text', 'N/A')}")
            
            if entry.get('translated_text'):
                print(f"\n   Translated text ({len(entry.get('translated_text', ''))} chars):")
                print(f"   {entry.get('translated_text', 'N/A')}")
            
            if entry.get('error'):
                print(f"\n   ❌ Error: {entry.get('error', 'N/A')}")
                if entry.get('error_details'):
                    print(f"   Details: {entry.get('error_details', 'N/A')}")
            
            print("-" * 100)
        
        # Calculate statistics
        total = len(logs)
        successful = sum(1 for log in logs if log.get('success', False))
        failed = total - successful
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total translations: {total}")
        print(f"   Successful: {successful} ({successful/total*100:.1f}%)" if total > 0 else "   Successful: 0")
        print(f"   Failed: {failed} ({failed/total*100:.1f}%)" if total > 0 else "   Failed: 0")
        
        if logs:
            # Language statistics
            source_langs = {}
            for log in logs:
                lang = log.get('source_lang', 'unknown')
                source_langs[lang] = source_langs.get(lang, 0) + 1
            
            print(f"\n🌐 Source Languages:")
            for lang, count in sorted(source_langs.items(), key=lambda x: x[1], reverse=True):
                print(f"   {lang}: {count} ({count/total*100:.1f}%)")
        
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_file}")
        print("   No translations have been logged yet.")
    except json.JSONDecodeError:
        print(f"❌ Error reading log file: Invalid JSON")
    except Exception as e:
        print(f"❌ Error: {e}")

def tail_translation_logs(log_file='/app/translations/libretranslate_log.json'):
    """Tail translation logs in real-time"""
    import time
    
    print("📋 Tailing translation logs... (Press Ctrl+C to stop)\n")
    
    last_size = 0
    last_entries = []
    
    try:
        while True:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                
                # Check for new entries
                if len(logs) > len(last_entries):
                    new_entries = logs[len(last_entries):]
                    
                    for entry in new_entries:
                        print(f"\n🆕 New Translation at {entry.get('timestamp', 'N/A')}")
                        print(f"   {entry.get('source_lang', 'N/A')} → {entry.get('target_lang', 'N/A')}")
                        print(f"   Original: {entry.get('original_text', 'N/A')[:100]}...")
                        if entry.get('translated_text'):
                            print(f"   Translated: {entry.get('translated_text', 'N/A')[:100]}...")
                        if entry.get('error'):
                            print(f"   ❌ Error: {entry.get('error', 'N/A')}")
                        print("-" * 60)
                    
                    last_entries = logs
                
            except:
                pass
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n✅ Stopped tailing logs")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View LibreTranslate translation logs')
    parser.add_argument('-n', '--number', type=int, default=10, 
                        help='Number of recent entries to show (default: 10)')
    parser.add_argument('-f', '--follow', action='store_true',
                        help='Follow log file (like tail -f)')
    parser.add_argument('--file', default='/app/translations/libretranslate_log.json',
                        help='Path to log file')
    
    args = parser.parse_args()
    
    if args.follow:
        tail_translation_logs(args.file)
    else:
        view_translation_logs(args.file, args.number)
