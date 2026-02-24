import requests
import os

# DejaVu fonts are reliable and widely available
FONTS = {
    "DejaVuSans-Bold.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf",
    "DejaVuSerif-Italic.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSerif-Italic.ttf",
    "Montserrat-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
    "Oswald-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf",
    "Impact.ttf": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf" # Anton is a good Impact alternative for open source
}

def download_fonts():
    os.makedirs("assets/fonts", exist_ok=True)
    for name, url in FONTS.items():
        path = os.path.join("assets/fonts", name)
        if not os.path.exists(path):
            print(f"Downloading {name}...")
            try:
                r = requests.get(url)
                r.raise_for_status()
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"[OK] Saved to {path}")
            except Exception as e:
                print(f"[ERR] Failed to download {name}: {e}")
                # Try alternate for Playfair if it fails
                if "Playfair" in name:
                     print("Trying alternate URL for Playfair...")
                     alt_url = "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/static/PlayfairDisplay-Italic.ttf"
                     try:
                        r = requests.get(alt_url)
                        r.raise_for_status()
                        with open(path, "wb") as f:
                            f.write(r.content)
                        print(f"[OK] Saved to {path}")
                     except Exception:
                        pass
        else:
            print(f"[OK] {name} already exists.")

if __name__ == "__main__":
    download_fonts()
