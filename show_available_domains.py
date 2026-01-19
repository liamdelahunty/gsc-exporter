import os
from collections import defaultdict

def get_available_domains():
    """
    Scans the 'output' directory and returns a list of available domains,
    formatted and grouped for command-line use.
    """
    output_dir = 'output'
    if not os.path.isdir(output_dir):
        print(f"Error: Directory '{output_dir}' not found.")
        return None

    try:
        domains_grouped = defaultdict(list)
        dir_names = [name for name in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, name))]

        for name in dir_names:
            # Heuristic to find the base domain (e.g., 'croneri.co.uk' from 'www.croneri.co.uk')
            parts = name.split('.')
            if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'ac', 'ltd']:
                base_domain = '.'.join(parts[-3:])
            elif len(parts) > 1:
                base_domain = '.'.join(parts[-2:])
            else:
                base_domain = name

            # If the directory name is the base domain, it's a domain property.
            # Otherwise, it's a URL-prefix property.
            if name == base_domain:
                output_string = f"sc-domain:{name}"
            else:
                output_string = f"https://{name}"
            
            domains_grouped[base_domain].append(output_string)
        
        return domains_grouped

    except OSError as e:
        print(f"Error reading directory '{output_dir}': {e}")
        return None

if __name__ == "__main__":
    domains_by_base = get_available_domains()
    if domains_by_base:
        print("Available sites for use in reports:\n")
        
        # Sort base domains alphabetically
        for base_domain in sorted(domains_by_base.keys()):
            print(f"# {base_domain}")
            
            properties = domains_by_base[base_domain]
            
            def sort_key(prop_string):
                """Sorts properties: sc-domain, then www, then alphabetically."""
                if prop_string.startswith('sc-domain:'):
                    return (0, prop_string)
                if '://www.' in prop_string:
                    return (1, prop_string)
                return (2, prop_string)

            for prop in sorted(properties, key=sort_key):
                print(prop)
            print("")
            
    else:
        print("No sites found in the 'output' directory.")
