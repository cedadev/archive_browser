const updateProgress = (count, total, failed) => {
  console.info("Updating progress: ", count, total, failed);
  const progressPercentage = Math.ceil((count / total) * 100) + 1;

  document.getElementById('count').textContent = count;
  document.getElementById('failed').textContent = failed;
  document.getElementsByClassName('progress-bar')[0].setAttribute('aria-valuenow', progressPercentage);
  document.getElementsByClassName('progress-bar')[0].style.width = `${progressPercentage}%`;
};

const download = async (url, stats) => {
  $('#progress').text(`Downloading: ${url}`);

  try {
      const response = await fetch(url);

      if (response.status === 403) { 
          console.warn(`Permission denied: ${url}`);
          stats.failureCount += 1;
      } else if (!response.ok) {
          console.error(`Error downloading ${url}: ${response.status} - ${response.statusText}`);
          stats.failureCount += 1;
      } else {
          stats.successCount += 1;
          return response.blob();
      }
  } catch (error) {
      console.error(`Network error downloading ${url}: ${error.message}`);
      stats.failureCount += 1;
  }

  updateProgress(stats.successCount + stats.failureCount, stats.totalFiles, stats.failureCount);
  return null;
};

const downloadByGroup = (paths, filesPerGroup = 5) => {
  const urls = paths.map(path => `https://dap.ceda.ac.uk${path}`);
  
  let stats = { successCount: 0, failureCount: 0, totalFiles: paths.length };

  document.getElementById('count').textContent = 0;
  document.getElementById('total').textContent = paths.length;
  document.getElementById('failed').textContent = 0;

  return Promise.map(urls, url => download(url, stats).then(() => updateProgress(stats.successCount + stats.failureCount, stats.totalFiles, stats.failureCount)), { concurrency: filesPerGroup })
      .then(blobs => {
          $('#progress').text("Zipping");
          return blobs.filter(blob => blob !== null);
      });
};

const exportZip = (blobs, paths) => {
  const zip = new JSZip();

  blobs.forEach((blob, i) => {
      const path = paths[i];
      const filename = path.split('/').pop();
      const folderPath = path.split('/').slice(1, -1).join('/');
      
      const folder = zip.folder(folderPath) || zip;
      folder.file(filename, blob);
  });

  zip.generateAsync({ type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 9 } })
      .then(zipFile => saveAs(zipFile, `combined-${Date.now()}.zip`));

  $('#progress').text("FINISHED - check browser downloads");
};

const downloadAndZip = (paths) => {
  return downloadByGroup(paths, 5).then(blobs => exportZip(blobs, paths));
};
