# Stellarium Lab

Personal agent workflow for exploring the sky and comparing telescope/eyepiece
combinations in the installed Stellarium desktop application.

- Read `README.md` for operation, equipment, and current verification limits.
- Shared application state belongs to `Development/config/dotfiles/stellarium/`.
  Do not create a second configuration copy here.
- Work personally. Preserve existing equipment, observer settings, and user data.
- Use the installed version's HTTP API. Read available properties before changing
  them; confirm the selected equipment and view after every transition.
- Session credentials and generated scripts stay in ignored `.local/`. Never
  commit passwords. If Stellarium's Save Settings persists a session password,
  close with `python3 stellarium.py quit` and inspect config.ini before staging.
- The workflow simulates an optical view; it does not control a physical mount
  or predict atmospheric seeing and all real eyepiece optical effects.
