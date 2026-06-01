# Start Terminal 1
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
cd 'C:\Users\moury\OneDrive\Desktop\web\DSA_Hint_Engine\solution';
.\ollama\Scripts\Activate.ps1;
uvicorn app.main:app --reload
"

# Start Terminal 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
ollama serve
"