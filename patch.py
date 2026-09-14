import os
import re
import sys

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original = content

    # 1. Universal Build.MANUFACTURER & Build.BRAND bypass to "samsung"
    if "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "sget-object" in line and "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in line:
                reg = line.strip().split()[1].replace(',', '')
                lines[i] = f'    const-string {reg}, "samsung"'
        content = "
".join(lines)

    if "Landroid/os/Build;->BRAND:Ljava/lang/String;" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "sget-object" in line and "Landroid/os/Build;->BRAND:Ljava/lang/String;" in line:
                reg = line.strip().split()[1].replace(',', '')
                lines[i] = f'    const-string {reg}, "samsung"'
        content = "
".join(lines)

    # 2. Neutralize root binary, test-keys, and su strings
    content = content.replace('"test-keys"', '"release-keys"')
    content = content.replace('"/system/bin/su"', '"/system/bin/no_su"')
    content = content.replace('"/system/xbin/su"', '"/system/xbin/no_su"')
    content = content.replace('"/sbin/su"', '"/sbin/no_su"')
    content = content.replace('"/system/app/Superuser.apk"', '"/system/app/none"')
    content = content.replace('"su"', '"no_su"')

    # 3. Completely replace method bodies for RootingCheckUtil / root checking classes
    if "RootingCheckUtil" in content or "checkSuExists" in content or "checkRootingPackage" in content or "checkForBinary" in content or "common_rooting_desc" in content:
        content = re.sub(
            r'(.method\s+[^{}\n]+?\([^{}\n]*?\)\s*Z)[\s\S]*?\.end method',
            r'\1\n    .registers 2\n    const/4 v0, 0x0\n    return v0\n.end method',
            content
        )

    # 4. Completely replace PackageValidator methods to return true (0x1)
    if "PackageValidator" in content or "9741A0F330DC2E8619B76A2597F308C37DBE30A2" in content:
        content = re.sub(
            r'(.method\s+[^{}\n]+?\([^{}\n]*?\)\s*Z)[\s\S]*?\.end method',
            r'\1\n    .registers 2\n    const/4 v0, 0x1\n    return v0\n.end method',
            content
        )

    # 5. Disable RootingDetectedDialog completely so it can never pop up
    if "RootingDetectedDialog" in content or "common_rooting_title" in content or "common_rooting_desc" in content:
        content = re.sub(
            r'(.method\s+[^{}\n]+?onCreateDialog\([^{}\n]*?\)[^{}\n]+?)[\s\S]*?\.end method',
            r'\1\n    .registers 2\n    const/4 v0, 0x0\n    return-object v0\n.end method',
            content
        )
        content = re.sub(
            r'(.method\s+[^{}\n]+?show\([^{}\n]*?\)\s*V)[\s\S]*?\.end method',
            r'\1\n    .registers 2\n    return-void\n.end method',
            content
        )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main(decompiled_dir):
    patched_count = 0
    for root, _, files in os.walk(decompiled_dir):
        for file in files:
            if file.endswith('.smali'):
                if patch_file(os.path.join(root, file)):
                    patched_count += 1
    print(f"Successfully patched {patched_count} smali files!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "decompiled"
    main(target)
