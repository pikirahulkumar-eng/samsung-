import os
import sys

NL = chr(10)

def patch_smali_methods(content):
    if '\n.method ' not in content:
        return content

    is_root_util = any(k in content for k in ['RootingCheckUtil', 'checkSuExists', 'checkRootingPackage'])
    is_validator = 'PackageValidator' in content
    is_root_dialog = 'RootingDetectedDialog' in content
    is_setup = 'SHealthMonitorSetupActivity' in content
    is_restriction = any(k in content for k in ['RestrictionView', 'isSupportedCountry', 'isSupportCountry', 'common_restriction', 'CommonConstants$SupportedType'])
    is_conn = any(k in content for k in ['ConnectionState', 'BaseEcgOnboardingCard', 'NoCompatibleWatchCard', 'showNoCompatibleDialog'])

    if not (is_root_util or is_validator or is_root_dialog or is_setup or is_restriction or is_conn):
        return content

    methods = content.split('\n.method ')
    res = [methods[0]]
    for m in methods[1:]:
        if '\n' not in m:
            res.append(m)
            continue
        header, body = m.split('\n', 1)
        
        # NEVER TOUCH CONSTRUCTORS
        if '<init>' in header:
            res.append(m)
            continue

        regs = '    .registers 2'
        for line in body.splitlines():
            s = line.strip()
            if s.startswith('.registers') or s.startswith('.locals'):
                regs = line
                break

        # 1. Root & Security checks: always false
        if is_root_util and header.strip().endswith(')Z'):
            new_m = header + NL + regs + NL + '    const/4 v0, 0x0' + NL + '    return v0' + NL + '.end method'
            res.append(new_m)
        # 2. Package validation: always true
        elif is_validator and header.strip().endswith(')Z'):
            new_m = header + NL + regs + NL + '    const/4 v0, 0x1' + NL + '    return v0' + NL + '.end method'
            res.append(new_m)
        # 3. Country support: always true
        elif any(k in header for k in ['isSupportCountry', 'isSupportedCountry', 'isCountrySupported', 'isEligible']) and header.strip().endswith(')Z'):
            new_m = header + NL + regs + NL + '    const/4 v0, 0x1' + NL + '    return v0' + NL + '.end method'
            res.append(new_m)
        # 4. Restriction check: always false
        elif any(k in header for k in ['isRestricted', 'isRestriction', 'checkRestriction']) and header.strip().endswith(')Z'):
            new_m = header + NL + regs + NL + '    const/4 v0, 0x0' + NL + '    return v0' + NL + '.end method'
            res.append(new_m)
        # 5. Country ISO / Code getters: return "US"
        elif any(k in header for k in ['getNetworkCountryIso', 'getSimCountryIso', 'getCountryCode']) and header.strip().endswith(')Ljava/lang/String;'):
            new_m = header + NL + regs + NL + '    const-string v0, "US"' + NL + '    return-object v0' + NL + '.end method'
            res.append(new_m)
        # 6. SupportedType methods: always return SUPPORTED (a)
        elif header.strip().endswith(')Lcom/samsung/android/shealthmonitor/util/CommonConstants$SupportedType;'):
            new_m = header + NL + regs + NL + '    sget-object v0, Lcom/samsung/android/shealthmonitor/util/CommonConstants$SupportedType;->a:Lcom/samsung/android/shealthmonitor/util/CommonConstants$SupportedType;' + NL + '    return-object v0' + NL + '.end method'
            res.append(new_m)
        # 7. ConnectionState methods: always return CONNECTED (b)
        elif header.strip().endswith(')Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;'):
            new_m = header + NL + regs + NL + '    sget-object v0, Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;->b:Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;' + NL + '    return-object v0' + NL + '.end method'
            res.append(new_m)
        # 8. Disable showErrorDialog & showNoCompatibleDialog
        elif (is_setup and 'showErrorDialog(' in header) or 'showNoCompatibleDialog' in header:
            if header.strip().endswith(')V'):
                new_m = header + NL + regs + NL + '    return-void' + NL + '.end method'
                res.append(new_m)
            else:
                res.append(m)
        # 9. Disable RootingDetectedDialog
        elif is_root_dialog:
            if 'onCreateDialog' in header:
                new_m = header + NL + regs + NL + '    const/4 v0, 0x0' + NL + '    return-object v0' + NL + '.end method'
                res.append(new_m)
            elif 'show(' in header:
                new_m = header + NL + regs + NL + '    return-void' + NL + '.end method'
                res.append(new_m)
            else:
                res.append(m)
        else:
            res.append(m)

    return '\n.method '.join(res)

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original = content

    # 1. Manufacturer & Brand bypass
    if "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "sget-object" in line and "Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;" in line:
                reg = line.strip().split()[1].replace(',', '')
                lines[i] = f'    const-string {reg}, "samsung"'
        content = NL.join(lines)

    if "Landroid/os/Build;->BRAND:Ljava/lang/String;" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "sget-object" in line and "Landroid/os/Build;->BRAND:Ljava/lang/String;" in line:
                reg = line.strip().split()[1].replace(',', '')
                lines[i] = f'    const-string {reg}, "samsung"'
        content = NL.join(lines)

    # 2. Force ConnectionState field read to always be CONNECTED (b)
    if "Lwf/g;->b:Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;" in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "iget-object" in line and "Lwf/g;->b:Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;" in line:
                reg = line.strip().split()[1].replace(',', '')
                lines[i] = f'    sget-object {reg}, Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;->b:Lcom/samsung/android/shealthmonitor/wearable/v2/common/ConnectionState;'
        content = NL.join(lines)

    # 3. Neutralize root binary, test-keys, and su strings
    content = content.replace('"test-keys"', '"release-keys"')
    content = content.replace('"/system/bin/su"', '"/system/bin/no_su"')
    content = content.replace('"/system/xbin/su"', '"/system/xbin/no_su"')
    content = content.replace('"/sbin/su"', '"/sbin/no_su"')
    content = content.replace('"/system/app/Superuser.apk"', '"/system/app/none"')
    content = content.replace('"su"', '"no_su"')

    # 4. Clean method body replacement
    content = patch_smali_methods(content)

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