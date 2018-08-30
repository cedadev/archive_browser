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

    // Make sure to add the settings
    var setup = function (user_options) {
        $.extend(options, user_options)
    };

    function generate_actions(ext, file) {

        var download_templ = "<a class='btn btn-lg' href='" + file + "'><i class=\"fa fa-download\" aria-hidden=\"true\"></i></a>"
        var plot_templ = "<a class=\"btn btn-lg\" href=\"javascript:Start('" + file + "?plot')\"><i class=\"fa fa-line-chart\" aria-hidden=\"true\"></i></a>"
        var view_templ = "<a class='btn btn-lg' href='" + file + "'><i class=\"fa fa-eye\" aria-hidden=\"true\"></i></a>"
        var subset_templ = "<a class='btn btn-lg' href='" + file + ".html'><i class=\"fa fa-cogs\" aria-hidden=\"true\"></i>\n</a>"

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
        filename = filename[filename.length -1];

        if (filename === "00README"){
            action_string = download_templ + view_templ;
        }
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

    function moles_icon(record_type){
        console.log(record_type)
        if (record_type === 'Dataset'){
            return "<i class=\"fas fa-database dataset\"></i>"
        } else {
            return "<i class=\"fas fa-copy collection\"></i>"
        }
    }

    // Get Directories from elasticsearch
    var addResults = function () {

        // Setup
        var table_string = "";
        var path = $('#' + options.pathID).val();
        var target = $('#' + options.resultsID);

        // Create queries
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
            "size": 1000
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
                        "path.keyword": path+"/"
                    }
                }
            );


            file_query.query = {
                "term": {
                    "info.directory": ""
                }
            };
        }


        // Render templates
        var dir_template = $('#dir_' + options.templateID).html();
        var file_template = $('#file_' + options.templateID).html();

        // Speeds up future use
        Mustache.parse(dir_template, options.customTags);
        Mustache.parse(file_template, options.customTags);

        // Get directories
        var dir_url = [options.host, options.dir_index, '_search'].join("/");
        var dir_results_string = "";

        console.log(JSON.stringify(dir_query))
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
                    } else if (dir_array[i]._source.readme !== undefined){
                        // Use the top line of the readme if there is one
                        desc = '<i class="fab fa-readme"></i>&nbsp;' + dir_array[i]._source.readme.split("\n")[0]
                    }

                    if (dir_array[i]._source.link !== undefined && dir_array[i]._source.link === true) {
                        link_target = Mustache.render("<a href='?path={{target}}' target='_blank'><i class='fas fa-link'></i></a>",
                            {
                                target: dir_array[i]._source.archive_path
                            })
                    }

                    dir_results_string = dir_results_string + Mustache.render(
                        dir_template,
                        {
                            path: dir_array[i]._source.path,
                            archive_path: dir_array[i]._source.archive_path,
                            item: dir_array[i]._source.dir,
                            link: link_target,
                            description: desc,
                            size: "",
                            actions: ""
                        }
                    )

                    dir_display_string = Mustache.render("Directories: ({{display}}/{{total}}) ",
                        {
                            display: dir_array.length,
                            total: data.hits.total
                        })

                }

                // Make sure dirs are before files
                if (table_string === "") {
                    table_string = table_string + dir_results_string
                } else {
                    table_string = dir_results_string + table_string
                }

                // Add results to table
                target.html(table_string)

            },
            contentType: "application/json",
            error: function (data) {
                console.log(data)
            }
        })

        // Get archive path
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
                    var archive_path = data.hits.hits[0]._source.archive_path

                    // Get Files
                    file_query.query.term["info.directory"] = archive_path
                    var file_url = [options.host, options.file_index, '_search'].join("/");
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
                                        item: file_array[i]._source.info.name,
                                        size: sizeText(file_array[i]._source.info.size),
                                        actions: generate_actions(ext, file_path),
                                        icon: getIcon(ext)
                                    }
                                )
                            }

                            table_string = table_string + file_results_string;

                            // Add results to table
                            target.html(table_string)

                        },
                        contentType: "application/json",
                        error: function (data) {
                            console.log(data)
                        }
                    })

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

                    if (collection._source.readme !== undefined){
                        $('#readmeButton').removeClass('hide')
                        var readme_split = collection._source.readme.split('\n');

                        var readme_html = "";
                        for (var i =0; i < readme_split.length; i++ ){
                            if (readme_split[i] !== ""){
                                readme_html += readme_split[i]+"<br>"
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



    // Explicitly reveal public pointers to the private functions
    // that we want to reveal publicly

    return {
        setup: setup,
        addResults: addResults,
    }
})();