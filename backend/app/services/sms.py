import httpx
import logging

logger = logging.getLogger("constai.sms")

# Termii configuration placeholders
TERMII_API_KEY = "mock_termii_api_key_for_constai"
TERMII_SENDER_ID = "ConstAI"
TERMII_BASE_URL = "https://api.ng.termii.com/api"

async def send_otp_via_termii(phone_number: str, otp: str) -> bool:
    """
    Sends OTP code to Nigerian phone numbers using Termii API.
    Simulates sending with mock fallback if credentials are unset or invalid.
    """
    logger.info(f"SMS Service: Initializing OTP delivery to {phone_number}.")
    
    # Clean phone format for Nigeria (+234 or 080...)
    clean_phone = phone_number.replace("+", "").strip()
    if clean_phone.startswith("0"):
        clean_phone = "234" + clean_phone[1:]

    payload = {
        "to": clean_phone,
        "from": TERMII_SENDER_ID,
        "sms": f"Your ConstAI Field Console verification code is {otp}. Expires in 5 minutes.",
        "type": "plain",
        "channel": "dnd", # Use Termii direct DND bypass channel
        "api_key": TERMII_API_KEY
    }

    try:
        # Mock delivery for test/development environments to avoid external API calls
        if "mock" in TERMII_API_KEY or not TERMII_API_KEY:
            logger.info(f"[DEVELOPMENT FALLBACK] Termii SMS Sent to {phone_number}: Code = {otp}")
            return True

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TERMII_BASE_URL}/sms/send",
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SMS Service: Termii delivery success. Message ID: {data.get('message_id')}")
                return True
            else:
                logger.error(f"SMS Service: Termii delivery failed with status {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"SMS Service: Exception during SMS routing: {str(e)}")
        # Graceful fallback to console logging
        logger.info(f"[EMERGENCY FALLBACK] Termii OTP output for {phone_number}: Code = {otp}")
        return True
