function treeNode_Edit()
{
    let selectedNodes = $("#tree-wrapper").jstree('get_selected', true);
    if (selectedNodes.length === 1)
    {
        let node = selectedNodes[0];

        if (node.type === 'folder') {
            let id = node.id.replace('folder', '');
            let modal = new AjaxModal("{% url 'modal_update_folder' 98765 %}".replace('98765', id));
            modal.setSubmitCallback(tree_Refresh);
            modal.loadAndShow();
        }
        else {
            let id = node.id.replace('sub', '');
            let modal = new AjaxModal("{% url 'modal_update_subscription' 98765 %}".replace('98765', id));
            modal.setSubmitCallback(tree_Refresh);
            modal.loadAndShow();
        }
    }
}

function treeNode_Delete()
{
    let selectedNodes = $("#tree-wrapper").jstree('get_selected', true);
    if (selectedNodes.length === 1)
    {
        let node = selectedNodes[0];

        if (node.type === 'folder') {
            let id = node.id.replace('folder', '');
            let modal = new AjaxModal("{% url 'modal_delete_folder' 98765 %}".replace('98765', id));
            modal.setSubmitCallback(tree_Refresh);
            modal.loadAndShow();
        }
        else {
            let id = node.id.replace('sub', '');
            let modal = new AjaxModal("{% url 'modal_delete_subscription' 98765 %}".replace('98765', id));
            modal.setSubmitCallback(tree_Refresh);
            modal.loadAndShow();
        }
    }
}

function tree_Initialize()
{
    let treeWrapper = $("#tree-wrapper");
    treeWrapper.jstree({
        core : {
            data : {
                url : "{% url 'ajax_get_tree' %}"
            },
            check_callback : tree_ValidateChange,
            themes : {
                dots : false
            },
        },
        types : {
            folder : {
                icon : "typcn typcn-folder"
            },
            sub : {
                icon : "typcn typcn-user",
                max_depth : 0
            }
        },
        plugins : [ "types", "wholerow", "dnd" ]
    });
    treeWrapper.on("changed.jstree", tree_OnSelectionChanged);
}

function tree_Refresh()
{
    $("#tree-wrapper").jstree("refresh");
}

function tree_ValidateChange(operation, node, parent, position, more)
{
    if (more.dnd)
    {
        // create_node, rename_node, delete_node, move_node and copy_node
        if (operation === "copy_node" || operation === "move_node")
        {
            if (more.ref.type === "sub")
                return false;
        }
    }

    return true;
}

function tree_OnSelectionChanged(e, data)
{
    let filterForm = $('#form_video_filter');
    let filterForm_folderId = filterForm.find('#form_video_filter_folder_id');
    let filterForm_subId = filterForm.find('#form_video_filter_subscription_id');

    let node = data.instance.get_selected(true)[0];

    // Fill folder/sub fields
    if (node === null) {
        filterForm_folderId.val('');
        filterForm_subId.val('');
    }
    else if (node.type === 'folder') {
        let id = node.id.replace('folder', '');
        filterForm_folderId.val(id);
        filterForm_subId.val('');
    }
    else {
        let id = node.id.replace('sub', '');
        filterForm_folderId.val('');
        filterForm_subId.val(id);
    }

    videos_Reload();
}

function videos_Reload()
{
    videos_Submit.call($('#form_video_filter'));
}

let videos_timeout = null;

function videos_ResetPageAndReloadWithTimer()
{
    let filters_form = $("#form_video_filter");
    filters_form.find('input[name=page]').val("1");

    clearTimeout(videos_timeout);
    videos_timeout = setTimeout(() => {
        videos_Reload();
        videos_timeout = null;
    }, 200);
}

function videos_PageClicked()
{
    // Obtain page from button
    let page = $(this).data('navigation-page');

    // Set page
    let filters_form = $("#form_video_filter");
    filters_form.find('input[name=page]').val(page);

    // Reload
    videos_Reload();
    $("html, body").animate({ scrollTop: 0 }, "slow");
}

function videos_Submit(e)
{
    let loadingDiv = $('#videos-loading');
    loadingDiv.fadeIn(300);

    let form = $(this);
    let url = form.attr('action');

    $.post(url, form.serialize())
        .done(result => {
            $("#videos-wrapper").html(result);
            $(".ajax-link").on("click", ajaxLink_Clicked);
            $(".btn-paging").on("click", videos_PageClicked);
        })
        .fail(() => {
            $("#videos-wrapper").html('<div class="alert alert-danger">An error occurred while retrieving the video list!</div>');
        })
        .always(() => {
            loadingDiv.fadeOut(100);
        });

    if (e !== null)
        e.preventDefault();
}

///
/// Notifications
///
const JOB_QUERY_INTERVAL = 1500;


function get_and_process_running_jobs()
{
    $.get("{% url 'ajax_get_running_jobs' %}")
        .done(data => {

            let progress = $('#status-progress');
            let jobPanel = $('#job_panel');
            let jobTitle = jobPanel.find('#job_panel_title');
            let jobTitleNoJobs = jobPanel.find('#job_panel_no_jobs_title');
            let jobTemplate = jobPanel.find('#job_panel_item_template');

            if (data.length > 0) {

                // Update status bar
                if (data.length > 1) {
                    $('#status-message').text(`Running ${data.length} jobs...`);
                }
                else {
                    $('#status-message').text(`${data[0].description} | ${data[0].message}`);
                }

                // Update global progress bar
                let combinedProgress = 0;
                for (let entry of data) {
                    combinedProgress += entry.progress;
                }

                let percent = 100 * combinedProgress / data.length;

                progress.removeClass('invisible');
                let bar = progress.find('.progress-bar');
                bar.width(`${percent}%`);
                bar.text(`${percent.toFixed(0)}%`);

                // Update entries in job list
                jobTitle.removeClass('collapse');
                jobTitleNoJobs.addClass('collapse');

                data.sort((a, b) => a.id - b.id);
                jobPanel.find('.job_entry').remove();

                for (let entry of data) {
                    let jobEntry = jobTemplate.clone();
                    jobEntry.attr('id', `job_${entry.id}`);
                    jobEntry.addClass('job_entry');
                    jobEntry.removeClass('collapse');
                    jobEntry.find('#job_panel_item_title').text(entry.description);
                    jobEntry.find('#job_panel_item_subtitle').text(entry.message);

                    let entryPercent = 100 * entry.progress;
                    let jobEntryProgress = jobEntry.find('#job_panel_item_progress');
                    jobEntryProgress.width(`${entryPercent}%`);
                    jobEntryProgress.text(`${entryPercent.toFixed(0)}%`);

                    jobEntry.appendTo(jobPanel);
                }

                $('#btn_toggle_job_panel').dropdown('update');
            }
            else {
                progress.addClass('invisible');
                $('#status-message').text("");

                jobTitle.addClass('collapse');
                jobTitleNoJobs.removeClass('collapse');
                jobPanel.find('.job_entry').remove();

                $('#btn_toggle_job_panel').dropdown('update');
            }
        });
}

///
/// Initialization
///
$(document).ready(() => {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();

    tree_Initialize();

    // Subscription toolbar
    $("#btn_create_sub").on("click", () => {
        let modal = new AjaxModal("{% url 'modal_create_subscription' %}");
        modal.setSubmitCallback(tree_Refresh);
        modal.loadAndShow();
    });
    $("#btn_create_folder").on("click", () => {
        let modal = new AjaxModal("{% url 'modal_create_folder' %}");
        modal.setSubmitCallback(tree_Refresh);
        modal.loadAndShow();
    });
    $("#btn_import").on("click", () => {
        let modal = new AjaxModal("{% url 'modal_import_subscriptions' %}");
        modal.setSubmitCallback(tree_Refresh);
        modal.loadAndShow();
    });
    $("#btn_edit_node").on("click", treeNode_Edit);
    $("#btn_delete_node").on("click", treeNode_Delete);

    // Videos filters
    let filters_form = $("#form_video_filter");
    filters_form.submit(videos_Submit);
    filters_form.find('input[name=query]').on('change', videos_ResetPageAndReloadWithTimer);
    filters_form.find('select[name=sort]').on('change', videos_ResetPageAndReloadWithTimer);
    filters_form.find('select[name=show_watched]').on('change', videos_ResetPageAndReloadWithTimer);
    filters_form.find('select[name=show_downloaded]').on('change', videos_ResetPageAndReloadWithTimer);
    filters_form.find('select[name=results_per_page]').on('change', videos_ResetPageAndReloadWithTimer);

    videos_Reload();

    // Notifications
    get_and_process_running_jobs();
    setInterval(get_and_process_running_jobs, JOB_QUERY_INTERVAL);
});
