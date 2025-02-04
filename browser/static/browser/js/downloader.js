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
          const blob = await response.blob(); 
          stats.successCount += 1;
          return blob;
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

  const processInChunks = async () => {
      const results = [];
      for (let i = 0; i < urls.length; i += filesPerGroup) {
          const batch = urls.slice(i, i + filesPerGroup).map(url => 
              download(url, stats).then(blob => {
                  updateProgress(stats.successCount + stats.failureCount, stats.totalFiles, stats.failureCount);
                  return blob;
              })
          );
          results.push(...(await Promise.all(batch)));
      }
      return results;
  };
  $('#progress').text("Zipping your data. Just a moment...");
  return processInChunks().then(blobs => {
      $('#progress').text("Zipping");
      return blobs.filter(blob => blob !== null);
  });
};

const exportZip = (blobs, paths) => {
  const zip = new JSZip();
  
  blobs.forEach((blob, index) => {
      if (!blob) return; // Skip failed downloads
      
      const path = paths[index];
      const filename = path.split('/').pop();
      const folderPath = path.split('/').slice(1, -1).join('/');

      const folder = zip.folder(folderPath) || zip;
      folder.file(filename, blob);
  });

  // Update UI to indicate compression is in progress
  $('#progress').text("Preparing ZIP file... This may take a while.");

  zip.generateAsync({ 
      type: 'blob', 
      compression: 'DEFLATE', 
      compressionOptions: { level: 5 } 
  }, (metadata) => {
      // Update progress UI during ZIP compression
      $('#progress').text(`Compressing: ${metadata.percent.toFixed(2)}%`);
  }).then(zipFile => {
      // Trigger the file download
      saveAs(zipFile, `combined-${Date.now()}.zip`);
      $('#progress').text("Download will start soon. Check browser downloads.");
  });
};

const downloadAndZip = (paths) => {
  return downloadByGroup(paths, 5).then(blobs => exportZip(blobs, paths));
};
