var DATASET_TOOLTIP = "These records describe and link to the actual data in our archive. They also provide spatial and temporal information, access and usage information and link to background information on why and how the data were collected."
var COLLECTION_TOOLTIP = "A collection of Datasets that share some common purpose, theme or association. These collections link to one or more Dataset records."

var ElasticBrowser = (function () {
    // Elasticsearch interaction to populate the file browser

    // Set default options
    const options = {
        customTags: ['<%', '%>'],
        resultsID: 'results',
        pathID: 'path'
    };

    let row_template;
    let link_template;
    let table_string;
    let target;
    let total_results;
    let file_url;
    let dir_url;
    let dir_results_string;


    // Make sure to add the settings
    const setup = function (user_options) {
        $.extend(options, user_options);

        // Load mustache templates
        row_template = $('#row_template').html();
        link_template = "<a href=\"{{path}}\">{{name}}</a>"

        // Speeds up future use
        Mustache.parse(row_template, options.customTags);
        Mustache.parse(link_template)

        // Results variables
        table_string = "";
        target = $('#' + options.resultsID);

    };

    function generate_actions(ext, file_name) {

        let subset_templ = "";

        // Generate button for download action
        let download_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}?download=1' title='Download file' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate(file_name),
                icon: "download"
            });

        // Generate button for view action
        let view_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='View file' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate(file_name),
                icon: "eye"
            });

        if (!USE_FTP){
            // Generate button for subset action
            subset_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='Extract subset' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
                {
                    url: pathManipulate(file_name, "opendap"),
                    icon: "cogs"
                });
        }

        // Build the correct action buttons for the file
        let action_string;
        switch (ext) {

            case "nc":
            case "hdf":
            case "h4":
            case "hdf4":
                action_string = download_templ + subset_templ;
                break;

            case "gif":
            case "jpg":
            case "jpeg":
            case "png":
            case "svg":
            case "svgz":
            case "wbmp":
            case "webp":
            case "ico":
            case "jng":
            case "bmp":
            case "txt":
            case "pdf":
            case "html":
                action_string = view_templ + download_templ;
                break;

            default:
                action_string = download_templ
        }

       if (file_name === '00README'){
            action_string = view_templ
       }

        return action_string
    }

    function getIcon(ext) {
        let icon;
        switch (ext) {
            case "dir":
                icon = "<span class=\"far fa-folder\"></span>"
                break;
            case "symlink":
                icon = "<span class=\"fas fa-link\" data-toggle=\"tooltip\" title=\"Symbolic link\"></span>"
                break;
            case "gz":
            case "zip":
            case "tar":
            case "tgz":
            case "bz2":
                icon = "<span class=\"far fa-file-archive\"></span>";
                break;
            case "png":
            case "gif":
            case "tif":
            case "TIF":
                icon = '<span class="far fa-file-image"></span>';
                break;
            case "txt":
                icon = '<span class="far fa-file-alt"></span>';
                break;
            case "html":
            case "xml":
                icon = '<span class="far fa-file-code"></span>';
                break;
            case "avi":
                icon = '<span class="far fa-file-video"></span>';
                break;
            default:
                icon = '<span class="far fa-file"></span>'

        }
        return icon
    }

    function moles_icon(record_type) {
        if (record_type === 'Dataset') {
            return Mustache.render("<i class='fas fa-database dataset' title='{{ tooltip }}' data-toggle='tooltip'></i>",
                {
                    tooltip: DATASET_TOOLTIP
                })
        } else {
            return Mustache.render("<i class='fas fa-copy collection' title='{{tooltip}}' data-toggle='tooltip'></i>",
                {
                    tooltip: COLLECTION_TOOLTIP
                });
        }
    }

    // Get Directories from elasticsearch
    const addResults = function () {

        // Setup
        const path = $('#' + options.pathID).val();

        dir_url = '/api/directory' + path;
        file_url = '/api/file' + path;

        // Get directories
        dir_results_string = "";

        // Set the API response counter
        let results_returned = 0;

        $.get({
            url: dir_url,
            success: function (data) {
                let dir_array = data.results;

                for (let i = 0; i < dir_array.length; i++) {

                    // Set defaults
                    let desc = "";
                    let info_templ = Mustache.render("<a class='btn btn-lg' href = '{{url}}' title = 'See catalogue entry' data-toggle='tooltip'><span class='fa fa-{{icon}}'></span></a>",
                        {
                            url: dir_array[i].url,
                            icon: 'info-circle'
                        });
                    let directory_icon = getIcon("dir");

                    // Template description column
                    if (dir_array[i].title !== undefined && data.render_titles) {
                        desc = Mustache.render("{{{icon}}}&nbsp;{{title}}",
                            {
                                title: dir_array[i].title,
                                icon: moles_icon(dir_array[i].record_type.toTitleCase())

                            })
                    } else if (dir_array[i].readme !== undefined) {
                        // Use the top line of the readme if there is one
                        let first_line_readme = dir_array[i].readme.split("\n")[0];

                        if (first_line_readme !== "HIDE DIRECTORY") {
                            desc = '<i class="fab fa-readme" title="Description taken from 00README" data-toggle="tooltip"></i>&nbsp;' + first_line_readme
                        } else {
                            desc = first_line_readme
                        }
                    }

                    // Change icon to display a link if the directory is a symlink
                    if (dir_array[i].link !== undefined && dir_array[i].link === true) {
                        directory_icon = getIcon("symlink")
                    }

                    // Where the directory is not hidden and type is dir
                    if (desc !== "HIDE DIRECTORY") {
                        if (dir_array[i].type === "dir") {
                            // Where there is MOLES information
                            if (dir_array[i].url !== undefined) {
                                dir_results_string = dir_results_string + Mustache.render(
                                    row_template,
                                    {
                                        icon: directory_icon,
                                        item: Mustache.render(link_template, {path: dir_array[i].archive_path, name: dir_array[i].dir}),
                                        description: desc,
                                        size: "",
                                        actions: info_templ
                                    }
                                )
                            }
                            // All other cases where the directory is not hidden, these do not have moles info
                            else {
                                dir_results_string = dir_results_string + Mustache.render(
                                    row_template,
                                    {
                                        icon: directory_icon,
                                        item: Mustache.render(link_template, {path: dir_array[i].archive_path, name: dir_array[i].dir}),
                                        description: desc,
                                        size: "",
                                        actions: ""
                                    }
                                )
                            }
                        } else if (dir_array[i].type === "file"){

                            // Handle cases where it has been through the fast queue but not the slow
                            if (dir_array[i].archive_path === undefined){
                                desc = "This file is a symlink. The link will be populated shortly."
                                dir_results_string = dir_results_string + Mustache.render(
                                    row_template,
                                    {
                                        row_attrs: 'class="text-muted"',
                                        icon: directory_icon,
                                        item: dir_array[i].dir,
                                        description: desc,
                                        size: "",
                                        actions: ""
                                    }
                                )
                            } else {

                                let file_name = dir_array[i].dir;
                                let ext = getExtension(file_name);

                                let row = Mustache.render(
                                    row_template,
                                    {
                                        icon: directory_icon,
                                        item: Mustache.render(link_template, {path: dir_array[i].archive_path, name: dir_array[i].dir}),
                                        description: desc,
                                        size: "",
                                        actions: generate_actions(ext, file_name)
                                    }
                                )
                                dir_results_string = dir_results_string + row
                            }
                        }
                    }
                }

                // Make sure dirs are before files
                if (table_string === "") {
                    table_string = table_string + dir_results_string
                } else {
                    table_string = dir_results_string + table_string
                }

                // Add results to table
                target.html(table_string);

                // Add dir results count to table
                if (data.result_count.relation === 'eq'){
                    $('#dir_count').html(data.result_count.value + " dirs")
                } else {
                    $('#dir_count').html(">" + data.result_count.value + " dirs")
                }

                results_returned++;
            },
            contentType: "application/json",
            complete: function (data) {
                if (results_returned === 2) {
                    $('#page_load').hide()
                }
            },
            error: function (data) {
                $('#page_load').html("An error occured retrieving the directories")
            }
        });

        // Get the files and collection link at the top of the page
        let file_results_string = "";

        $.get({
            url: file_url,
            success: function (data) {

                if (!$.isEmptyObject(data.parent_dir)) {
                    let file_array = data.results;

                    let i;
                    for (i = 0; i < file_array.length; i++) {

                        let file_name = file_array[i].info.name;
                        let ext = getExtension(file_name);

                        if (file_array[i].info.location === 'on_tape') {

                            file_results_string = file_results_string + Mustache.render(
                                row_template,
                                {
                                    row_attrs: 'class="text-muted"',
                                    icon: getIcon(ext),
                                    item: file_array[i].info.name,
                                    size: sizeText(file_array[i].info.size),
                                    actions: "<a class='btn btn-lg' href='/storage_types#on_tape' title='File on tape' data-toggle='tooltip'><i class='fa fa-info-circle'></i></a>",

                                }
                            )

                        } else {
                            file_results_string = file_results_string + Mustache.render(
                                row_template,
                                {
                                    icon: getIcon(ext),
                                    item: Mustache.render(link_template, {path: pathManipulate(file_name), name:file_name}),
                                    size: sizeText(file_array[i].info.size),
                                    actions: generate_actions(ext, file_name),

                                }
                            )
                        }
                    }

                    table_string = table_string + file_results_string;

                    // Add results to table
                    target.html(table_string);

                    // Update total results variable
                    total_results = data.result_count.value;

                    // Add file results count to table
                    if (data.result_count.relation === 'eq'){
                        $('#file_count').html(formatNumber(total_results) + " files")
                    } else {
                        $('#file_count').html(">" + formatNumber(total_results) + " files")
                    }
                    // Add the collection link above the results table
                    let collection = data.parent_dir;

                    // Make sure there is a title
                    if (collection.title !== undefined) {

                        let catalogue_entry = Mustache.render("<a class='pl-1' href = '{{url}}' title = 'See catalogue entry' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
                            {
                                url: collection.url,
                                icon: "info-circle"
                            });

                        let collection_link = Mustache.render("<h4>{{{collection_type}}}&nbsp;{{title}}&nbsp;{{{button}}}</h4>",
                            {
                                collection_type: moles_icon(collection.record_type.toTitleCase()),
                                title: collection.title,
                                button: catalogue_entry

                            }
                        );


                        $('#collection_link').html(collection_link)

                    } else {
                        $('#collection_link').html("")
                    }

                    if (collection.readme !== undefined) {
                        $('#readmeButton').removeClass('hide');
                        let readme_split = collection.readme.split('\n');

                        let readme_html = "";
                        for (let i = 0; i < readme_split.length; i++) {
                            if (readme_split[i] !== "") {
                                readme_html += readme_split[i] + "<br>"
                            }
                        }

                        $('#readmeContent div').html(escapeHtml(readme_html))
                    }

                    results_returned++
                    console.log(results_returned)


                } else if (path !== "/") {
                    // If there are no results in the directory index then we should revert
                    // to THREDDS to see if there is a directory in the archive which has just
                    // been missed by the Elasticsearch indexing tools. This should be a
                    // directory because we have already checked for a file in the Django view.

                    $('#page_load').hide();
                    $('.table').hide();
                    let dap_link = Mustache.render("<a href='{{{url}}}'>Try in live view.</a>",
                        {
                            url: pathManipulate("","catalog")
                        });
                    $('.messages:first').html(
                                "<div class=\"alert alert-success text-center\"><h4>Not found in archive index. " + dap_link +"</h4></div>"
                            )
                }
            },
            contentType: "application/json",
            complete: function (data) {

                if (total_results > options.max_files_per_page) {

                    // Render message at top and bottom of page to tell the user there are more results than shown
                    $(".messages").each(function () {
                        $(this).html(Mustache.render(
                            "<div class=\"alert alert-danger text-center\">Too many files in current directory. Displaying {{ max_files }}/{{ display }} files.<a class=\"btn btn-primary btn-sm ml-2\" role='button' onclick='ElasticBrowser.getAll()' id='show_all'>Show All</a></div>",
                            {
                                max_files: formatNumber(options.max_files_per_page),
                                display: formatNumber(total_results)
                            }))
                    })
                }
                if (results_returned === 2){
                    $('#page_load').hide()
                }
            },
            error: function (data) {
                $('#page_load').html("An error occured retrieving the files")
            }
        });

    };

    const getAllResults = function getAllResults() {

        const path = $('#' + options.pathID).val();
        let show_all_url = '/api/file' + path + '?show_all=true';
        let file_results_string = "";

        // Show loading icon in button
        $('a[id="show_all"]').each( function () {
            $(this).html("Retrieving Results&nbsp;<img src='/static/browser/img/loading.gif' style='height: 19px'/>"
            )
        });

        $.get({
            url: show_all_url,
            success: function (data) {

                let file_array = data.results;

                for (let i = 0; i < file_array.length; i++) {
                    let file_name = file_array[i].info.name;
                    let ext = getExtension(file_name);

                    file_results_string = file_results_string + Mustache.render(
                        row_template,
                        {
                            icon: getIcon(ext),
                            item: Mustache.render(link_template, {path: pathManipulate(file_name), name:file_name}),
                            size: sizeText(file_array[i].info.size),
                            actions: generate_actions(ext, file_name),
                        }
                    )
                }

                table_string = dir_results_string + file_results_string;

                // Add results to table
                target.html(table_string)

            },
            contentType: "application/json",
            error: function (data) {
                console.log(data)
            },
            complete: function (data) {
                $(".messages").each(function () {
                    $(this).html("")
                })

            }
        })
    };

    // Explicitly reveal pointers to the functions
    // that we want to reveal publicly
    return {
        setup: setup,
        addResults: addResults,
        getAll: getAllResults,
    }
})();