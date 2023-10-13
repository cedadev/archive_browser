


////console.log(decodedData)

//const regex = /'path': '(.*?)'/g;
//const paths = [];
//let match;

//while ((match = regex.exec(decodedData)) !== null) {
 // paths.push('https://dap.ceda.ac.uk'+match[1]);
//}

//console.log(paths)

const download = async (url) => {
    $('#progress').text(url);
  try {
    const response = await fetch(url);
    if (response.ok) {
      return response.blob();
    } else if (response.status === 404) {
      console.error(`File not found: ${url}`);
      return null; // Skip this URL if not found
    } else {
      throw new Error(`Error downloading ${url}: ${response.statusText}`);
    }
  } catch (error) {
    console.error(`Error downloading ${url}: ${error.message}`);
    return null; // Handle other errors
  }
};

const downloadByGroup = (paths, files_per_group=5) => {
  var urls = new Array(); 
  paths.forEach(path => {urls.push("https://dap.ceda.ac.uk"+path)})  
  return Promise.map(
    urls, 
    async url => {
      return await download(url);
    },
    {concurrency: files_per_group}
  );
}

const exportZip = blobs => {
  const zip = new JSZip();

  blobs.forEach((blob, i) => {
    const path = paths[i];
    const filename = path.substring(path.lastIndexOf('/') + 1);
    const pathParts = path.split('/').slice(1, -1); 

    let folder = zip.folder(); // Start with the root folder

    // Create nested folders
    pathParts.forEach(part => {
      folder = folder.folder(part);
    });

    folder.file(filename, blob); // Add the file to the appropriate folder
  });

  zip.generateAsync({
    type: 'blob',
    compression: 'DEFLATE',
    compressionOptions: { level: 9 }
  }).then(zipFile => {
    const currentDate = new Date().getTime();
    const fileName = `combined-${currentDate}.zip`;
    return saveAs(zipFile, fileName);
  });
  $('#progress').text("FINISHED - check browser downloads");
};

const downloadAndZip = paths => {
  return downloadByGroup(paths, 5).then(exportZip);
}