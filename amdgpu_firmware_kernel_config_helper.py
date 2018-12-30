#!/usr/bin/python3
import sys
import os


def list_amdgpu_firmware_codenames() -> list:
    fw_files = []
    for dir_entry in os.scandir('/lib/firmware/amdgpu'):
        if dir_entry.is_file():
            fw_files.append(dir_entry.name)
    fw_prefixes = []
    for fw_file in fw_files:
        fw_prefix = fw_file.split('_')[0]
        if not fw_prefix in fw_prefixes:
            fw_prefixes.append(fw_prefix)
    fw_prefixes = sorted(fw_prefixes)
    return fw_prefixes


def print_usage():
    print('Usage: {} <gpu_codename>'.format(sys.argv[0]))
    print('    where <gpu_codename> is one of:')
    gpu_codenames = list_amdgpu_firmware_codenames()
    for codename in gpu_codenames:
        print('        {}'.format(codename))


def get_kernel_version() -> str:
    os_version_info = os.uname()
    return os_version_info.release


def get_CONFIG_EXTRA_FIRMWARE_line(codename: str) -> str:
    ret = ''
    fw_files = []
    for dir_entry in os.scandir('/lib/firmware/amdgpu'):
        if dir_entry.is_file():
            if dir_entry.name.startswith(codename + '_'):
                fw_files.append(dir_entry.name)
    fw_files = sorted(fw_files)
    #print(fw_files)
    for fw_file in fw_files:
        ret += ' amdgpu/' + fw_file
    ret = ret.strip()
    return ret


def check_kernel_config(kernel_version: str) -> bool:
    config_fn = '/usr/src/linux-{}/.config'.format(kernel_version)
    print('Checking kernel for existing firmware config: {}...'.format(config_fn))
    with open(config_fn, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('CONFIG_EXTRA_FIRMWARE'):
                print('Found existing firmware config line:')
                print(line)
                return True
    return False


def write_new_kernel_config(kernel_version, extra_fw_line) -> bool:
    config_fn = '/usr/src/linux-{}/.config'.format(kernel_version)
    config_fn_new = '/usr/src/linux-{}/.config.new'.format(kernel_version)
    print('Writing new version of kernel config: {}...'.format(config_fn_new))
    orig_lines = []
    try:
        f = open(config_fn, 'rt', encoding='utf-8')
        for line in f:
            line = line.rstrip()
            orig_lines.append(line)
        f.close()

        f = open(config_fn_new, 'wt', encoding='utf-8')
        for line in orig_lines:
            if line.startswith('CONFIG_EXTRA_FIRMWARE='):
                print('Replacing firmware config line...')
                # print(line)
                # print('To:')
                # print(extra_fw_line)
                f.write("CONFIG_EXTRA_FIRMWARE=\"{}\"\n".format(extra_fw_line))
            else:
                f.write(line + "\n")
        f.close()
    except IOError as ioe:
        print(str(ioe))
        return False
    return True


def main():

    if len(sys.argv) < 2:
        print_usage()
        return

    if sys.argv[1] == '--help':
        print_usage()
        return

    gpu_codename = sys.argv[1]

    existing_codenames = list_amdgpu_firmware_codenames()
    if not gpu_codename in existing_codenames:
        print('GPU codename \'{}\' not found! Existing codenames are: {}'.format(
            gpu_codename, ', '.join(existing_codenames)))
        return

    kernel_version = get_kernel_version()

    print('Chosen GPU codename:', gpu_codename)
    print('Current kernel version:', kernel_version)

    extra_fw_line = get_CONFIG_EXTRA_FIRMWARE_line(gpu_codename)

    if not check_kernel_config(kernel_version):
        print('CONFIG_EXTRA_FIRMWARE is missing in your kernel config! You should enable CONFIG_FW_LOADER!')
        return

    if not write_new_kernel_config(kernel_version, extra_fw_line):
        print('Error writing kernel configs. Check you write access to /usr/src/linux-{}'.format(kernel_version))
        if os.geteuid() != 0:
            print('Run me with sudo?')
        return

    print('OK')
    print('')
    print('Now you can check your kernel directory for a file:')
    print('    /usr/src/linux-{}/.config.new'.format(kernel_version))
    print('And if it is OK, replace original config with a new one.')
    print('')
    print('git diff follows:')
    print('')
    config_orig = '/usr/src/linux-{}/.config'.format(kernel_version)
    config_next = '/usr/src/linux-{}/.config.new'.format(kernel_version)
    # os.spawnlp(os.P_NOWAIT, 'git', 'git', 'diff', config_orig, config_next) # bad, breaks terminal
    os.system('git diff \"{}\" \"{}\"'.format(config_orig, config_next))


if __name__ == '__main__':
    main()

