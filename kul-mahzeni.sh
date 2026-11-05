#!/bin/bash
# Kül Mahzeni başlatıcısı (uygulama menüsünden çağrılır)
export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:$PATH"
cd "$HOME/kul-mahzeni" || exit 1
exec uv run --with pygame-ce python main.py >"$HOME/kul-mahzeni/son-calisma.log" 2>&1
