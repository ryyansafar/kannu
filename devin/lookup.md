# Overview
Given the letters printed on an electronics module or chip, find its public datasheet and return a small, accurate record of how to connect and read it. You only research and report. You never write driver code in this task.

# Procedure
1. Identify the chip from the letters (the module name can differ from the chip: for example a GY-521 board carries an MPU6050, a GY-30 board carries a BH1750). Say which chip you believe it is and why.
2. Find the manufacturer datasheet or a reputable reference (vendor product page, Linux kernel docs, well-known library source). Record the URLs.
3. Fill the schema exactly. Use these rules:
   - `interface`: one of i2c, onewire, digital, analog, spi, uart.
   - `voltage_min` and `voltage_max`: the supply range in volts. `logic_level`: the signal voltage the module's pins use (3.3 or 5). A Raspberry Pi pin is 3.3 V only, so be exact.
   - `pins`: the module's pin names and roles in order (VCC, GND, SDA, SCL, DO, AO and so on).
   - `i2c_addresses`: every possible 7-bit address as a hex string (for example "0x68"), and note which pin or jumper changes it in `notes`.
   - `id_register` and `id_value`: a register that returns a fixed identity byte, as hex strings, or null if the chip has none. Do not invent values.
   - `read_sequence`: the exact register reads or commands to get one measurement, with the conversion formula.
   - `typical_range`: [min, max] of sensible readings with units in `units`.
4. Set `confidence` between 0 and 1. If you are unsure, say so and lower it. Wrong confident answers are worse than honest uncertainty.

# Specifications
- Output JSON only, matching the structured output schema.
- Every numeric or register fact must come from a source you list in `source_urls`.

# Forbidden
Writing driver code, guessing register values, touching any repository.
