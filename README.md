# Kannu

A Raspberry Pi that watches its own sensors, says "I am not sure" instead of lying, and files its own bug report. A Devin session turns the report into a failing test and a fix, the Pi proves the fix on its real sensor, and a human merges.

Built for Devin Hacks Kochi (24 Oct 2026), Track: *Make the invisible visible*.

## The loop
1. **Sense:** the Pi reads a sensor and watches the I2C bus, the 1-Wire list and free pins for anything new.
2. **Guard (plain code, no network):** an empty read, a bad checksum, the 85-degree power-on value, a jump, a stuck value or an out-of-range reading puts the device in a safe state within 2 seconds.
3. **Report:** the Pi freezes the last 30 seconds and files a GitHub issue with a short context block.
4. **Fix:** a Devin session writes a failing test, a handler and a pull request.
5. **Prove:** the Pi runs the test on its real sensor.
6. **Merge:** a plain-code gate checks everything; a human presses the button.

## New sensors
Type the letters on a sensor; a Devin session reads the datasheet and returns a record; plain code checks it against the chip's identity register and the advisor shows which pins to connect. The Pi never drives an unknown pin.

## Run the tests
```bash
python3 -m venv .venv && .venv/bin/pip install pytest pytest-cov fastapi uvicorn requests httpx jsonschema tiktoken
.venv/bin/python -m pytest -q
```

## Licence
MIT.

## Socials & Support
- Portfolio: https://ryyansafar.site
- GitHub: https://github.com/ryyansafar
- Buy Me a Coffee: https://buymeacoffee.com/ryyansafar
- PayPal: https://www.paypal.com/paypalme/ryyansafar
- Razorpay: https://razorpay.me/@ryyansafar
