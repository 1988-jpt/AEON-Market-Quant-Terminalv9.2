# Crear el APK en Windows con WSL2

## 1. Instalar WSL2
Abra PowerShell como administrador:

```powershell
wsl --install -d Ubuntu-24.04
```

Reinicie Windows. Abra Ubuntu y cree su usuario y contraseña.

Compruebe desde PowerShell:

```powershell
wsl -l -v
```

Ubuntu debe aparecer con VERSION 2.

## 2. Instalar el entorno en Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-virtualenv \
  autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo6 cmake libffi-dev libssl-dev automake autopoint gettext curl

curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"

python3 -m virtualenv ~/venv_aeon
source ~/venv_aeon/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install buildozer cython==0.29.34
```

## 3. Copiar el proyecto al sistema Linux
No compile dentro de `/mnt/c/...`; es más lento y suele causar errores de permisos.

Ejemplo, si el ZIP está en Descargas de Windows:

```bash
mkdir -p ~/proyectos/aeon
cd ~/proyectos/aeon
cp "/mnt/c/Users/Usuario Final/Downloads/AEON_Market_Quant_Terminal_V8_APK_Ready.zip" .
unzip AEON_Market_Quant_Terminal_V8_APK_Ready.zip
cd AEON_Market_Quant_Terminal_V8_Professional
```

Cambie `Usuario Final` por el nombre real de su carpeta de Windows.

## 4. Construir el APK de prueba

```bash
source ~/venv_aeon/bin/activate
cd ~/proyectos/aeon/AEON_Market_Quant_Terminal_V8_Professional
buildozer android debug
```

La primera compilación puede tardar bastante porque descarga Android SDK, NDK y Gradle. Acepte las licencias escribiendo `y` cuando se solicite.

El APK se generará en:

```text
bin/
```

## 5. Copiar el APK a Windows

```bash
mkdir -p "/mnt/c/Users/Usuario Final/Downloads/AEON_APK"
cp bin/*.apk "/mnt/c/Users/Usuario Final/Downloads/AEON_APK/"
```

## 6. Instalar en Android
Active en el teléfono la instalación desde fuentes desconocidas para el explorador que abrirá el APK. Después copie el APK al teléfono e instálelo.

## Comandos útiles

Compilar nuevamente:

```bash
buildozer android debug
```

Limpiar una compilación dañada:

```bash
buildozer android clean
rm -rf .buildozer
buildozer android debug
```

Ver el registro del teléfono mediante USB:

```bash
buildozer android deploy run logcat
```

## Nota
Esta versión genera un APK solo para `arm64-v8a`, adecuado para la mayoría de teléfonos Android actuales y con un tamaño menor. El servicio en segundo plano está declarado como servicio foreground y no ejecuta órdenes reales.
