# api-server/audio_modules/vad_wrapper.py
"""
Compatibility wrapper for different versions of silero-vad
"""
import torch
import logging

logger = logging.getLogger(__name__)

def load_silero_vad_model():
    """Load Silero VAD model with version compatibility"""
    try:
        # Try new API (5.x)
        from silero_vad import load_silero_vad
        model = load_silero_vad(onnx=False)
        logger.info("✅ Loaded Silero VAD 5.x")
        return model, "5.x"
    except Exception as e:
        logger.warning(f"Failed to load with 5.x API: {e}")
        
        # Try alternative import
        try:
            import silero_vad
            model, utils = silero_vad.load(onnx=False)
            logger.info("✅ Loaded Silero VAD with alternative API")
            return model, "alt"
        except Exception as e2:
            logger.error(f"Failed to load Silero VAD: {e2}")
            raise

def get_speech_timestamps_compat(audio, model, model_version="5.x", **kwargs):
    """Get speech timestamps with version compatibility"""
    
    if model_version == "5.x":
        try:
            from silero_vad import get_speech_timestamps
            return get_speech_timestamps(audio, model, **kwargs)
        except ImportError:
            # Try alternative
            from silero_vad import VADIterator
            vad_iterator = VADIterator(model)
            
            # Process in chunks
            timestamps = []
            chunk_size = 512
            
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i:i + chunk_size]
                speech_dict = vad_iterator(chunk, return_seconds=False)
                if speech_dict:
                    timestamps.append(speech_dict)
            
            return timestamps
    else:
        # For older versions
        speech_timestamps = model(audio, **kwargs)
        return speech_timestamps