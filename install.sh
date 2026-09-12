# Cosmo Installer - run this once after downloading/cloning repo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$SCRIPT_DIR/app.py"

case "$(basename "$SHELL")" in
    zsh)
        PROFILE="$HOME/.zshrc"
        ;;
    bash)
        PROFILE="$HOME/.bash_profile"
        ;;
    *)
        echo "Could not detect zsh or bash automatically"
        echo "Please add the following line to your shell profile manually:"
        echo " alias cosmo=\"python3 $APP_PATH\""
        exit 1
        ;;

esac

ALIAS_LINE="alias cosmo=\"python3 $APP_PATH\""

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