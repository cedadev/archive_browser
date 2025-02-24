const url = "https://dap.ceda.ac.uk/badc/ukmo-cet/data/v1.0.0.0/daily/max/dlycet_max_1878_onwards.dat?download=1";

async function test() {
  console.log(url);
  try {
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const blob = await response.blob();

    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'dlycet_max_1878_onwards.dat';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Error fetching the file:', error);
  }
}