import shutil
import subprocess
import urllib.request
import time

def _download(url, path):
    """Download a file from the given URL to the specified path."""
    try:
        with urllib.request.urlopen(url) as response:
            with open(path, 'wb') as outfile:
                shutil.copyfileobj(response, outfile)
    except Exception as e:
        print("Failed to download:", url)
        raise e

def argoTunnel():
    """
    Sets up an Argo tunnel using the cloudflared binary.
    Downloads and unpacks the binary, starts the tunnel, and retrieves the hostname.

    Returns:
        str: The hostname of the tunnel, or None if an error occurred.
    """
    # Download and unpack the cloudflared binary
    try:
        _download("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb", "cloudflared.tgz")
        shutil.unpack_archive("cloudflared.tgz", extract_dir="cloudflared")
    except Exception as e:
        print("Error downloading or unpacking cloudflared:", e)
        return None

    # Start the cloudflared process
    try:
        cfd_proc = subprocess.Popen(
            ["./cloudflared/cloudflared", "tunnel", "--url", "ssh://localhost:22", "--logfile", "cloudflared.log", "--metrics", "localhost:49589"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
    except Exception as e:
        print("Error starting cloudflared:", e)
        return None

    # Allow some time for the process to start
    time.sleep(5)

    if cfd_proc.poll() is not None:
        print("Cloudflared failed to start. Check cloudflared.log for details.")
        return None

    # Extract the hostname from the metrics endpoint
    hostname = None
    for _ in range(20):
        try:
            with urllib.request.urlopen("http://127.0.0.1:49589/metrics") as response:
                text = response.read().decode()
                marker = 'cloudflared_tunnel_user_hostnames_counts{userHostname="https://'
                start = text.find(marker)
                if start != -1:
                    end = text.find('"', start + len(marker))
                    hostname = text[start + len(marker):end]
                    break
        except Exception:
            time.sleep(1)

    if not hostname:
        print("Failed to retrieve hostname from cloudflared metrics.")
        cfd_proc.terminate()
        return None

    return hostname

# Example usage
if __name__ == "__main__":
    tunnel_hostname = argoTunnel()
    if tunnel_hostname:
        print("Argo Tunnel created successfully:", tunnel_hostname)
    else:
        print("Failed to create Argo Tunnel.")
