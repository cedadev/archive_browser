var DATASET_TOOLTIP = "These records describe and link to the actual data in our archive. They also provide spatial and temporal information, access and usage information and link to background information on why and how the data were collected."
var COLLECTION_TOOLTIP = "A collection of Datasets that share some common purpose, theme or association. These collections link to one or more Dataset records."

var ElasticBrowser = (function () {
    // Elasticsearch interaction to populate the file browser

    // Set default options
    var options = {
        host: "http://jasmin-es1.ceda.ac.uk",
        customTags: ['<%', '%>'],
        resultsID: 'results',
        templateID: 'template',
        pathTitleID: 'path_title',
        pathID: 'path'
    };

    var file_template;
    var dir_template;
    var table_string;
    var target;
    var total_results;
    var archive_path;
    var file_url;
    var dir_url;
    var dir_results_string;


    // Make sure to add the settings
    var setup = function (user_options) {
        $.extend(options, user_options)

        // Load mustache templates
        dir_template = $('#dir_' + options.templateID).html();
        file_template = $('#file_template').html();

        // Speeds up future use
        Mustache.parse(dir_template, options.customTags);
        Mustache.parse(file_template, options.customTags);

        // Results variables
        table_string = "";
        target = $('#' + options.resultsID);

        // Indexes
        file_url = [options.host, options.file_index, '_search'].join("/");
        dir_url = [options.host, options.dir_index, '_search'].join("/");

    };


    function generate_actions(ext, file) {
        // javascript:Start('http://data.ceda.ac.uk/badc/namblex/data/aber-radar-1290mhz/20020801//aber-radar-1290mhz_macehead_20020801_hig-res-1h-1.na?plot')

        var file_name = file.split("/").slice(-1)[0];

        // Generate button for download action
        var download_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='Download file' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate(options.path_prefix, file_name),
                icon: "download"
            });

        // Generate button for plotting action
        var plot_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='Plot data' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate("javascript:Start('" + options.path_prefix, file_name + "?plot')"),
                icon: "chart-line"
            });

        // Generate button for view action
        var view_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='View file' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate(options.path_prefix, file_name),
                icon: "eye"
            });

        // Generate button for subset action
        var subset_templ = Mustache.render("<a class='btn btn-lg' href='{{url}}' title='Extract subset' data-toggle='tooltip'><i class='fa fa-{{icon}}'></i></a>",
            {
                url: pathManipulate(options.path_prefix, file_name + ".html"),
                icon: "cogs"
            });

        // Build the correct action buttons for the file
        var action_string;
        switch (ext) {
            case "na":
                action_string = download_templ + plot_templ
                break;

            case "nc":
                action_string = download_templ + subset_templ;
                break;

            case "txt":
            case "html":
                action_string = view_templ;
                break;

            default:
                action_string = download_templ
        }

        var filename = file.split('/');
        filename = filename[filename.length - 1];

        return action_string
    }

    function getIcon(ext) {
        var icon
        switch (ext) {
            case "gz":
            case "zip":
            case "tar":
            case "tgz":
            case "bz2":
                icon = "far fa-file-archive";
                break;
            case "png":
            case "gif":
            case "tif":
            case "TIF":
                icon = "far fa-file-image";
                break;
            case "txt":
                icon = "far fa-file-alt";
                break;
            case "html":
            case "xml":
                icon = "far fa-file-code";
                break;
            case "avi":
                icon = "far fa-file-video";
                break;
            default:
                icon = "far fa-file"

        }
        return icon
    }

    function generateExceptions(exceptions) {
        var must_not = [];

        for (var i = 0; i < exceptions.length; i++) {
            must_not.push(
                {
                    "term": {
                        "path.keyword": exceptions[i]
                    }
                }
            )
        }

        must_not.push(
            {
                "regexp": {
                    "dir.keyword": "[.].*"
                }
            }
        )

        return must_not
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
    var addResults = function () {

        // Setup
        var path = $('#' + options.pathID).val();

        var dir_query = {
            "sort": {
                "dir.keyword": {
                    "order": "asc"
                }
            },
            "query": {
                "bool": {
                    "must": [],
                    "must_not": generateExceptions(options.exceptions),
                    "filter": {
                        "term": {
                            "depth": path.split("/").length
                        }
                    }
                }
            },
            "size": 1000
        };

        var file_query = {
            "sort": {
                "info.name": {
                    "order": "asc"
                }
            },
            "size": options.max_files_per_page
        };

        var collection_query = {
            "query": {
                "term": {
                    "path.keyword": path
                }
            }
        };

        if (path === '/') {
            dir_query.query.bool.filter.term.depth = 1

            file_query.query = {
                "term": {
                    "info.directory": "/"
                }
            };
        } else {
            dir_query.query.bool.must.push(
                {
                    "prefix": {
                        "path.keyword": path + "/"
                    }
                }
            );


            file_query.query = {
                "term": {
                    "info.directory": ""
                }
            };
        }


        // Get directories
        dir_results_string = "";

        $.post({
            url: dir_url,
            data: JSON.stringify(dir_query),
            success: function (data) {
                var dir_array = data.hits.hits

                var all_same = false

                if (dir_array.length > 1) {
                    all_same = dir_array.every((val, i, arr) => val._source.title === arr[0]._source.title
                )
                }


                var i;
                for (i = 0; i < dir_array.length; i++) {
                    var desc = "";
                    var link_target = "";

                    if (dir_array[i]._source.title !== undefined && !all_same) {
                        desc = Mustache.render("<a href='{{{url}}}'>{{{icon}}}&nbsp;{{title}}</a>",
                            {
                                url: dir_array[i]._source.url,
                                title: dir_array[i]._source.title,
                                icon: moles_icon(dir_array[i]._source.record_type.toTitleCase())
                            })
                    } else if (dir_array[i]._source.readme !== undefined) {
                        // Use the top line of the readme if there is one
                        var first_line_readme = dir_array[i]._source.readme.split("\n")[0]

                        if (first_line_readme !== "HIDE DIRECTORY") {
                            desc = '<i class="fab fa-readme" title="Description taken from 00README" data-toggle="tooltip"></i>&nbsp;' + dir_array[i]._source.readme.split("\n")[0]
                        } else {
                            desc = first_line_readme
                        }
                    }

                    if (dir_array[i]._source.link !== undefined && dir_array[i]._source.link === true) {
                        link_target = Mustache.render("<a href='?path={{target}}' target='_blank'><i class='fas fa-link'></i></a>",
                            {
                                target: dir_array[i]._source.archive_path
                            })
                    }

                    if (desc !== "HIDE DIRECTORY") {
                        dir_results_string = dir_results_string + Mustache.render(
                            dir_template,
                            {
                                path: dir_array[i]._source.path,
                                item: dir_array[i]._source.dir,
                                description: desc,
                                size: "",
                                actions: ""
                            }
                        )
                    }

                }

                dir_results_string = dir_results_string
                // Make sure dirs are before files
                if (table_string === "") {
                    table_string = table_string + dir_results_string
                } else {
                    table_string = dir_results_string + table_string
                }

                // Add results to table
                target.html(table_string)

                // Add dir results count to table
                $('#dir_count').html(data.hits.total + " dirs")

            },
            contentType: "application/json",
            error: function (data) {
                console.log(data)
            }
        })

        // Check directories index for directory. Return the archive path for the directory.
        // Then search the archive path in the files index to return the files.
        $.post({
            url: dir_url,
            data: JSON.stringify({
                "query": {
                    "term": {
                        "path.keyword": path
                    }
                }
            }),
            success: function (data) {
                if (data.hits.hits.length === 1) {
                    archive_path = data.hits.hits[0]._source.archive_path

                    // Get Files
                    file_query.query.term["info.directory"] = archive_path
                    var file_results_string = "";

                    $.post({
                        url: file_url,
                        data: JSON.stringify(file_query),
                        success: function (data) {
                            var file_array = data.hits.hits

                            var i;
                            for (i = 0; i < file_array.length; i++) {
                                var file_path = [file_array[i]._source.info.directory, file_array[i]._source.info.name].join('/')
                                var ext = getExtension(file_path)

                                file_results_string = file_results_string + Mustache.render(
                                    file_template,
                                    {
                                        icon: getIcon(ext),
                                        item: file_array[i]._source.info.name,
                                        size: sizeText(file_array[i]._source.info.size),
                                        actions: generate_actions(ext, file_path)
                                    }
                                )
                            }

                            table_string = table_string + file_results_string;

                            // Add results to table
                            target.html(table_string)

                            // Update total results variable
                            total_results = data.hits.total

                            // Add file results count to table
                            $('#file_count').html(data.hits.total + " files")


                        },
                        contentType: "application/json",
                        complete: function (data) {
                            if (total_results > options.max_files_per_page) {

                                $(".messages").each(function () {
                                    $(this).html(Mustache.render(
                                        "<div class=\"alert alert-danger text-center\">Too many files in current directory. Displaying {{ max_files }}/{{ display }} files.<a class=\"btn btn-primary btn-sm ml-2\" role='button' onclick='ElasticBrowser.getAll()' id='show_all'>Show All</a></div>",
                                        {
                                            max_files: formatNumber(options.max_files_per_page),
                                            pydap_url: PYDAP_URL + window.location.pathname,
                                            display: formatNumber(total_results)
                                        }))
                                })
                            }
                        },
                        error: function (data) {
                            console.log(data)
                        }
                    })

                } else if (data.hits.hits.length === 0 && path != "/") {
                    window.location.replace(PYDAP_URL + window.location.pathname)
                }
            },
            contentType: "application/json"
        })


        // Get collection link and readme
        $.post({
            url: dir_url,
            data: JSON.stringify(collection_query),
            success: function (data) {
                var collection = data.hits.hits[0]

                if (data.hits.total === 1) {

                    if (collection._source.title !== undefined) {

                        var collection_link = Mustache.render("<h3>{{{collection_type}}}&nbsp;<a href='{{{url}}}'>{{title}}</a></h3>",
                            {
                                url: collection._source.url,
                                collection_type: moles_icon(collection._source.record_type.toTitleCase()),
                                title: collection._source.title
                            }
                        )

                        $('#collection_link').html(collection_link)

                    } else {
                        $('#collection_link').html("")
                    }

                    if (collection._source.readme !== undefined) {
                        $('#readmeButton').removeClass('hide')
                        var readme_split = collection._source.readme.split('\n');

                        var readme_html = "";
                        for (var i = 0; i < readme_split.length; i++) {
                            if (readme_split[i] !== "") {
                                readme_html += readme_split[i] + "<br>"
                            }
                        }

                        $('#readmeContent div').html(readme_html)
                    }

                }


            },
            contentType: "application/json",
            error: function (data) {
                console.log(data)
            }
        })
    }

    function getAllResults() {

        $('a[id="show_all"]').each( function () {
            $(this).html("<img src='/static/browser/img/loading.gif' style='height: 19px'></img>"
            )
        })

        var file_results_string = ""

        $.get({
            url: window.location.origin + "/show_all" + archive_path,
            success: function (data) {

                var file_array = data.results

                var i;
                for (i = 0; i < file_array.length; i++) {
                    var file_path = [file_array[i]._source.info.directory, file_array[i]._source.info.name].join('/')
                    var ext = getExtension(file_path)

                    file_results_string = file_results_string + Mustache.render(
                        file_template,
                        {
                            icon: getIcon(ext),
                            item: file_array[i]._source.info.name,
                            size: sizeText(file_array[i]._source.info.size),
                            actions: generate_actions(ext, file_path)
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

    }


    // Explicitly reveal public pointers to the private functions
    // that we want to reveal publicly

    return {
        setup: setup,
        addResults: addResults,
        getAll: getAllResults,
    }
})();