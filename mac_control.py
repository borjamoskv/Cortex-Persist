import subprocess


def speak(text):
    subprocess.run(["say", text])


def main():
    speak("Iniciando control soberano de este terminal.")
    print("Modo Mac Control Total activado.")


if __name__ == "__main__":
    main()
