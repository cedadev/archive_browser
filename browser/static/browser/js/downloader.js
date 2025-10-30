BASE_URL = "https://dap.ceda.ac.uk"
const TOKEN_URL = `${window.location.origin}/self`;


const TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI4ZjhmaUpyaUtDY3hmaHhzdU5vazVEekdJdFZ4amhhTWNJa05ZX2U4MnhJIn0.eyJleHAiOjE3NDgwOTUxODksImlhdCI6MTc0NzgzNTk4OSwianRpIjoiYzAyYTZhODktZGIzYS00N2NmLTk5NmEtNmYwNmYwMjNiNjRjIiwiaXNzIjoiaHR0cHM6Ly9hY2NvdW50cy5jZWRhLmFjLnVrL3JlYWxtcy9jZWRhIiwic3ViIjoiNzhhMzRlMzYtZjM4MC00NGY2LThmZmItNTQ3NDk0OWNjYjExIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoic2VydmljZXMtcG9ydGFsLWNlZGEtYWMtdWsiLCJzZXNzaW9uX3N0YXRlIjoiZjZlOTlkZmUtOWFiMy00NjgxLTgyMzItMmM1Y2Q0ZjU3ZjQ5IiwiYWNyIjoiMSIsInNjb3BlIjoiZW1haWwgb3BlbmlkIHByb2ZpbGUgZ3JvdXBfbWVtYmVyc2hpcCIsInNpZCI6ImY2ZTk5ZGZlLTlhYjMtNDY4MS04MjMyLTJjNWNkNGY1N2Y0OSIsImdyb3VwX21lbWJlcnNoaXAiOlsidWttb193eCJdLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwib3BlbmlkIjoiaHR0cHM6Ly9jZWRhLmFjLnVrL29wZW5pZC9BZHJpYW4uRGVic2tpIiwibmFtZSI6IkFkcmlhbiBEZWJza2kiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhZGVic2tpIiwiZ2l2ZW5fbmFtZSI6IkFkcmlhbiIsImZhbWlseV9uYW1lIjoiRGVic2tpIiwiZW1haWwiOiJhZHJpYW4uZGVic2tpQHN0ZmMuYWMudWsifQ.Rsq9elmMcDN3mmiMwZMgvQwX8nq53Q2A1tp7bfsNUG_VN0_aoS9apVTJ_fDdirObZJWs7Jz13S_Vmj_o0aXAebL6WW3myOGaqm9hZU4V1xmKPDY1WHsEfHKhMayQAYJP8D63cWfY0JZIqhVzNOeiOE6MAi0MnNiykqSUmzGs09hUetsX0jl-OgPmdoCUKohILE7LvKIhFYE77j80gVjTTTBy3P0A6MuJhp2hLnGpoBVH2ZjovaAs0TON8AZfbR8Yp_mVetEIgQZHSzfCGHgnLHFFPc47CeM4u-Kwoneh2RvZNRdcGEJbfzLy5HL70UJbXYcPxA6DEWqdonp-8O8QSw'


// get token from /self endpoint
async function get_token() {
  try {
    const response = await fetch(TOKEN_URL);

    if (response.ok) {
      const json = await response.json();
      return TOKEN;
      // return json.access_token;
    } else {
      console.log("Unauthorized");
      return null;
    }
  } catch (err) {
    console.error("Error fetching token:", err);
    return null;
  }
}

// update indicators of progress 
const updateProgress = (count, total, failed) => {
  const progressPercentage = Math.ceil((count / total) * 100) + 1;

  document.getElementById('successCount').textContent = count;
  document.getElementById('failureCount').textContent = failed;
  document.getElementsByClassName('progress-bar')[0].setAttribute('aria-valuenow', progressPercentage);
  document.getElementsByClassName('progress-bar')[0].style.width = `${progressPercentage}%`;
};

// retry download with exponential backoff
const delayRetry = async (attempt, url) => {
  const delay = Math.pow(2, attempt) * 500;
  console.warn(`Retrying ${url} in ${delay / 1000}s...`);
  await new Promise(res => setTimeout(res, delay));
}

// download a single file
const download = async (url, stats, token, maxRetries = 5) => {
  $('#progress').text(`Downloading: ${url}`);

  console.log("Downloading: ", url);
  let attempt = 0;

  headers = {};
  if (token != null) {
    headers['Authorization'] = "Bearer " + token;
  }

  params = {
    credentials: "same-origin",
    redirect: "error",
    headers: headers
  };
  
  result = null

  while (attempt <= maxRetries) {
    try {
      const response = await fetch(url, params);
      console.warn("Response status: ", response.status);
      if (response.status === 403 || response.status === 302) {
        console.warn(`Permission denied or redirect received: ${url}`);
        stats.failureCount += 1;
        failureAlert(stats.failureCount, token);
        break;
      }
  
      if (response.status === 500 || !response.ok) {
        console.error(`Error downloading ${url}: ${response.status} - ${response.statusText}`);
        attempt += 1;
        if (attempt <= maxRetries) {
          await delayRetry(attempt, url);
          continue;
        }
        stats.failureCount += 1;
        failureAlert(stats.failureCount, token);
        break;
      }
  
      const blob = await response.blob();
      stats.successCount += 1;
      result = blob;
      break;

    } catch (error) {
      console.error(`Unexpected error downloading ${url}: ${error.message}`);
      stats.failureCount += 1;
      failureAlert(stats.failureCount, token);
      break;
    }
  }
  updateProgress(stats.successCount + stats.failureCount, stats.totalFiles, stats.failureCount);
  return result;
};

const failureAlert = (failedCount, token) => {
  if (failedCount == 1) {
    if (!token) {
      alert("Some files are not available. Please, log in and try again.");
    }
    else {
      alert("Some files are not available. You may not have access.");
    }
  }

};

const downloadByGroup = async (paths, filesPerGroup = 5) => {
  const urls = paths.map(path => `${BASE_URL}${path}`);
  let stats = { successCount: 0, failureCount: 0, totalFiles: paths.length };

  const token = await get_token();
  console.log("Token: ", token);
  
  const processInChunks = async () => {
    const results = [];
    for (let i = 0; i < urls.length; i += filesPerGroup) {
      const batch = urls.slice(i, i + filesPerGroup).map(url =>
        download(url, stats, token).then(blob => {
          return blob;
        })
      );
      results.push(...(await Promise.all(batch)));
    }
    return results;
  };
  
  

  $('#progress').text("Zipping your data. Just a moment...");
  const blobs = await processInChunks();
  $('#progress').text("Zipping");

  failureAlert(stats.failureCount, token);
  return blobs.filter(blob => blob !== null);
};

const exportZip = (blobs, paths) => {
  const zip = new JSZip();
  if (blobs.length == 0) return;
  
  blobs.forEach((blob, index) => {
    const path = paths[index];
    const filename = path.split('/').pop();
    const folderPath = path.split('/').slice(1, -1).join('/');

    const folder = zip.folder(folderPath) || zip;
    folder.file(filename, blob);
  });

  $('#progress').text("Preparing ZIP file... This may take a while.");

  zip.generateAsync({
    type: 'blob',
    compression: 'DEFLATE',
    compressionOptions: { level: 5 }
  }, (metadata) => {
    $('#progress').text(`Compressing: ${metadata.percent.toFixed(2)}%`);
  }).then(zipFile => {
    saveAs(zipFile, `combined-${Date.now()}.zip`);
    $('#progress').text("Download will start soon. Check browser downloads.");
  });
};

const downloadAndZip = async (paths) => {
  return downloadByGroup(paths, 5).then(blobs => {exportZip(blobs, paths)});
};





