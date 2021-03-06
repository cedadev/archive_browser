function round(value, decimals) {
    // Round a number to specified decimals
    return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals);
}

function escapeHtml(text) {
    'use strict';
    return text.replace(/[\"&'\/<>]/g, function (a) {
        return {
            '"': '&quot;', '&': '&amp;', "'": '&#39;',
            '/': '&#47;',  '<': '&lt;',  '>': '&gt;'
        }[a];
    });
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


function getExtension(file) {
    // Extract the extension from a file path
    var re = /(?:\.([^.]+))?$/;
    return re.exec(file)[1]
}

function copyPath() {
    var copyText = $('#path').val()
    var copyBtn = $('#copy')

    var tempInput = document.createElement('input')
    tempInput.style = "position: absolute; left: -1000px; top: -1000px"
    tempInput.value = copyText
    document.body.appendChild(tempInput)
    tempInput.select()
    document.execCommand('copy')
    document.body.removeChild(tempInput)
}

// Tooltips

function hideTooltip (){
}
$('#copy').mouseleave(function () {
    $(this).tooltip('hide')
    $(this).attr("data-original-title","Copy directory path")

})

$('#copy').click(function () {
    $(this).attr("data-original-title","Copied!")
    $(this).tooltip('show')
    copyPath()
})

function Start(page) {
    // Open a new window to display the plotted data
    OpenWin = this.open(page, "PlotWindow",
        "toolbar=no,menubar=yes,location=no,scrollbars=yes,resizable=yes,width=850,height=650");
    OpenWin.focus();
}

function pathManipulate(postfix, type){
    // Used to build the correct path in order to initiate actions in pydap
    let path = window.location.pathname;

    let download_template = Mustache.render("{{{download_service}}}{{{ directory }}}/{{filename}}",
            {
                download_service: DOWNLOAD_SERVICE,
                directory: path,
                filename: postfix
            });

    let opendap_template = Mustache.render("{{{download_service}}}/thredds/dodsC{{{ directory }}}/{{filename}}.html",
        {
            download_service: DOWNLOAD_SERVICE,
            directory: path,
            filename: postfix
        });

    switch (type){

        case "opendap":
            return opendap_template;
        default:
            return download_template
    }


}

function formatNumber (num) {
    // Comma separate thousands
    return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1,")
}




