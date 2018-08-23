function round(value, decimals) {
    // Round a number to specified decimals
    return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals);
}

function sizeText(size) {
    // Take a number of bytes and form a string with the correct suffix
    var output_string;

    if (size < 1000) {
        output_string = Math.round(size) + " bytes";

    } else if (size < Math.pow(10, 6)) {
        output_string = round(size / 1000, 1) + " KB";

    } else if (size < Math.pow(10, 9)) {
        output_string = round(size / Math.pow(10, 6), 1) + " MB";

    } else {
        output_string = round(size / Math.pow(10, 9), 1) + " GB"
    }

    return output_string
}

String.prototype.toTitleCase = function () {
    return this.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};

function truncate30(string) {
    if (string.length > 30) {
        return string.slice(0,30) + "..."
    } else {
        return string
    }

}

function getExtension(file) {
    // Extract the extension from a file path
    var re = /(?:\.([^.]+))?$/;
    return re.exec(file)[1]
}

function copyPath() {
    var copyText = $('#path').val()
    var copyBtn = $('#copyButton')
    copyBtn.attr('data-original-title',"Copied: " + copyText)
    copyBtn.tooltip('show')

    var tempInput = document.createElement('input')
    tempInput.style = "position: absolute; left: -1000px; top: -1000px"
    tempInput.value = copyText
    document.body.appendChild(tempInput)
    tempInput.select()
    document.execCommand('copy')
    document.body.removeChild(tempInput)

}

function hideTooltip (){
    var copyBtn = $('#copyButton').tooltip('hide')
}


$(function () {
  $('[data-toggle="tooltip"]').tooltip({
      trigger: 'manual'
  })
})

function Start(page) {
    // Open a new window to display the plotted data
    OpenWin = this.open(page, "PlotWindow",
        "toolbar=no,menubar=yes,location=no,scrollbars=yes,resizable=yes,width=850,height=650");
    OpenWin.focus();
}

function OpenHelpWin(page) {
    win = this.open (page, "Help",
    "toolbar=yes,menubar=no,location=no,scrollbars=yes,resizable=yes,width=600,height=500");
    win.focus();
}

$(document).ready(function () {
    // Setup the page and load the data

    // Set options
    var options = {
        dir_index: "ceda-dirs",
        file_index: "ceda-level-2",
        exceptions: ["/sparc","/edc","/bodc"]
    };

    // Load the data
    ElasticBrowser.setup(options);
    ElasticBrowser.addResults();

})

