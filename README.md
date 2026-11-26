# HS RADAR SYSTEM X — Windows project

## What this is
A native Windows desktop control interface for an Arduino UNO + HC-05 educational radar project.

## Build on GitHub from an Android phone
1. Create a **public** GitHub repository named `HS-RADAR-SYSTEM-X`.
2. Upload `main.py` and `requirements.txt` to the repository root.
3. Create `.github/workflows/build-windows.yml` and paste the workflow from this project.
4. Commit the files to the `main` branch.
5. Open the repository's **Actions** tab.
6. Open the run named `Build HS RADAR SYSTEM X for Windows`.
7. Wait until it shows a green check mark.
8. Under **Artifacts**, download `HS_RADAR_SYSTEM_X-Windows`.
9. Extract the ZIP. It contains `HS_RADAR_SYSTEM_X.exe`.

## HC-05 pairing and use
1. On the Windows computer that will run the EXE, pair the HC-05 in Windows Bluetooth settings.
2. Find the outgoing Bluetooth COM port in Windows Device Manager > Ports (COM & LPT), or check Bluetooth device port settings.
3. Open the EXE, refresh COM ports, select the HC-05 outgoing COM port, choose 9600 baud, then Connect.
4. The app sends ASCII commands ending in a newline.
5. Demo mode does not send commands to hardware.

## Expected telemetry
The app shows raw serial messages in the log. It also recognizes optional readings such as:
- `D=15.2,A=90`
- `DIST=15.2 ANG=90`

Your Arduino firmware must actually send one of these formats for distance/angle panels to update. The app does not invent sensor data.

## Important
- This EXE is for Windows 10/11 x64, not Android.
- Pairing and COM-port access happen on the Windows computer where the EXE runs.
- Windows may display a SmartScreen warning because the EXE is unsigned.
- The command names must match your Arduino firmware. This project does not change your Arduino wiring or firmware.
- Do not publish private credentials, personal tokens, or unrelated files in the public repository.
