import os
import sys

def patch_smali(decompiled_dir):
    patched_count = 0
    for root, _, files in os.walk(decompiled_dir):
        for file in files:
            if file.endswith('.smali'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                new_content = content

                # 1. Bypass Build.MANUFACTURER checks across all smali files
                if "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in new_content:
                    lines = new_content.splitlines()
                    for i, line in enumerate(lines):
                        if "sget-object" in line and "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in line:
                            reg = line.strip().split()[1].replace(',', '')
                            lines[i] = f'    const-string {reg}, "samsung"'
                    new_content = "\n".join(lines)
                    patched_count += 1

                # 2. Bypass Build.BRAND checks
                if "Landroid/os/Build;->BRAND:Ljava/lang/String;" in new_content:
                    lines = new_content.splitlines()
                    for i, line in enumerate(lines):
                        if "sget-object" in line and "Landroid/os/Build;->BRAND:Ljava/lang/String;" in line:
                            reg = line.strip().split()[1].replace(',', '')
                            lines[i] = f'    const-string {reg}, "samsung"'
                    new_content = "\n".join(lines)
                    patched_count += 1

                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)

    print(f"Successfully applied patches to {patched_count} smali files!")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "decompiled"
    patch_smali(target_dir)
