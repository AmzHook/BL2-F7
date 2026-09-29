# Uploading this scaffold to GitHub

## Browser method

1. On GitHub, create a new repository named `BL2-F7`.
2. Do not initialize it with another README if you intend to upload this package as-is.
3. Use **Add file → Upload files**.
4. Upload the repository contents while preserving folders. If the browser makes hidden folders inconvenient, use GitHub Desktop or Git instead; `.github/workflows/build-bl2-f7.yml` must be present in the repository.
5. Commit the files.
6. Open **Actions → Build BL2-F7 Android → Run workflow**.
7. Start with `instrumented`.
8. After the build succeeds, download the APK from the **Artifacts** area at the bottom of the workflow run.

## Git command method

```bash
git init
git add .
git commit -m "Initial BL2-F7 build scaffold"
git branch -M main
git remote add origin https://github.com/YOUR_USER/BL2-F7.git
git push -u origin main
```

Then use **Actions → Build BL2-F7 Android → Run workflow**.
