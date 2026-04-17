import urllib.request
import os
import time
import sys

URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
FILE = "models/model.gguf"

def download_resumable():
    os.makedirs("models", exist_ok=True)
    
    # Get total size
    req = urllib.request.Request(URL, method="HEAD")
    with urllib.request.urlopen(req) as response:
        total_size = int(response.headers.get('Content-Length', 0))
    
    print(f"Total model size: {total_size / (1024*1024):.1f} MB")
    
    while True:
        downloaded = os.path.getsize(FILE) if os.path.exists(FILE) else 0
        if downloaded >= total_size:
            print("\nDownload complete!")
            break
            
        print(f"\nResuming from {downloaded / (1024*1024):.1f} MB ({(downloaded/total_size)*100:.1f}%)")
        
        req = urllib.request.Request(URL)
        req.add_header("Range", f"bytes={downloaded}-")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response, open(FILE, "ab") as out_file:
                start_time = time.time()
                last_print = start_time
                chunk_size = 1024 * 64
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    now = time.time()
                    if now - last_print > 2:
                        speed = len(chunk) / (now - last_print + 0.001) / 1024
                        print(f"Progress: {(downloaded/total_size)*100:.1f}% | {downloaded/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB | {speed:.1f} KB/s", end="\r")
                        last_print = now
                        
        except Exception as e:
            print(f"\nNetwork interrupted: {e}. Retrying in 2 seconds...")
            time.sleep(2)

if __name__ == "__main__":
    download_resumable()
