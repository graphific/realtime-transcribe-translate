#!/usr/bin/env python3
# test_translation.py - Test translation services

import sys
sys.path.insert(0, '/app')

from audio_modules.translation_utils import TranslationManager
import logging

logging.basicConfig(level=logging.INFO)

def test_translations():
    """Test translation services with sample texts"""
    
    print("\n🔍 Testing Translation Services")
    print("=" * 60)
    
    # Initialize translation manager
    manager = TranslationManager(preferred_service='libretranslate')
    
    # Get service info
    info = manager.get_service_info()
    print(f"Current service: {info['service_name']}")
    print(f"Available: {info['available']}")
    print()
    
    if not manager.translator:
        print("❌ No translation service available!")
        return
    
    # Test texts in different languages
    test_texts = [
        ("Hola, ¿cómo estás?", "es", "Spanish"),
        ("Bonjour, comment allez-vous?", "fr", "French"),
        ("Olá, como você está?", "pt", "Portuguese"),
        ("Ciao, come stai?", "it", "Italian"),
        ("Hallo, wie geht es dir?", "de", "German"),
        ("こんにちは", "ja", "Japanese"),
        ("你好", "zh", "Chinese"),
    ]
    
    print("Testing translations to English:")
    print("-" * 60)
    
    for text, lang, lang_name in test_texts:
        print(f"\n{lang_name} ({lang}):")
        print(f"  Original: {text}")
        
        try:
            translation = manager.translate(text, source_lang=lang, target_lang='en')
            if translation:
                print(f"  Translation: {translation}")
            else:
                print(f"  Translation: ❌ Failed")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test auto-detection
    print("\n\nTesting auto-detection:")
    print("-" * 60)
    
    auto_text = "Это тестовое сообщение"
    print(f"Text: {auto_text}")
    try:
        translation = manager.translate(auto_text, source_lang='auto', target_lang='en')
        if translation:
            print(f"Translation: {translation}")
        else:
            print("Translation: ❌ Failed")
    except Exception as e:
        print(f"Error: {e}")
    
    # Get stats if available
    if hasattr(manager.translator, 'get_stats'):
        print("\n\nTranslation Statistics:")
        print("-" * 60)
        manager.translator.get_stats()

if __name__ == "__main__":
    test_translations()
