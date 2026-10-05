# Cosmo Installer - run this once after downloading/cloning repo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$SCRIPT_DIR/app.py"

# Find the real interpreter path, so 'cosmo' always uses the Python that has the packages
PYTHON="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
if [ -z "$PYTHON" ]; then
    echo "No working python3 found. Install Python 3.11+ from python.org, then re-run."
    exit 1
fi
echo "Using Python: $PYTHON"

# Installing into conda's base environment can break conda's own tools
if [ "${CONDA_DEFAULT_ENV:-}" = "base" ]; then
    echo "Conda's base environment is active. Create a separate environment first:"
    echo "    conda create -n cosmo python=3.11 -y"
    echo "    conda activate cosmo"
    echo "then run this installer again."
    exit 1
fi

"$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"

case "$(basename "$SHELL")" in
case "$(basename "$SHELL")" in
    zsh)
        PROFILE="$HOME/.zshrc"
        ;;
    bash)
         # macOS terminals read .bash_profile; Linux terminals read .bashrc
        if [ "$(uname)" = "Darwin" ]; then
            PROFILE="$HOME/.bash_profile"
        else
            PROFILE="$HOME/.bashrc"
        fi
        ;;
esac

ALIAS_LINE="alias cosmo='\"$PYTHON\" \"$APP_PATH\"'"

if grep -Fxq "$ALIAS_LINE" "$PROFILE" 2>/dev/null; then
    echo "Already Installed - 'cosmo' is already set in $PROFILE"
else
    echo "" >> "$PROFILE"
    echo "# Added by Cosmo's install.sh" >> "$PROFILE"
    echo "$ALIAS_LINE" >> "$PROFILE"
    echo "Added 'cosmo' command to $PROFILE"

fi

echo ""
echo "Setup complete! Open a NEW terminal window (or run: source $PROFILE)"
echo "then type 'cosmo' from anywhere to launch the app."