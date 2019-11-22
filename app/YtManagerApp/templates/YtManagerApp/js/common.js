
function zeroFill(number, width) {
    width -= number.toString().length;
    if ( width > 0 ) {
        return new Array( width + (/\./.test( number ) ? 2 : 1) ).join( "0" ) + number;
    }
    return String(number); // always return a string
}

class AjaxModal
{
    constructor(url)
    {
        this.wrapper = $("#modal-wrapper");
        this.loading = $("#modal-loading");
        this.url = url;
        this.modal = null;
        this.form = null;
        this.submitCallback = null;
        this.modalLoadingRing = null;
    }

    setSubmitCallback(callback) {
        this.submitCallback = callback;
    }

    _showLoading() {
        this.loading.fadeIn(500);
    }

    _hideLoading() {
        this.loading.fadeOut(100);
    }

    _showModal() {
        if (this.modal !== null)
            this.modal.modal();
    }

    _hideModal() {
        if (this.modal !== null)
            this.modal.modal('hide');
    }

    _load(result) {
        this.wrapper.html(result);

        this.modal = this.wrapper.find('.modal');
        this.form = this.wrapper.find('form');
        this.modalLoadingRing = this.wrapper.find('#modal-loading-ring');

        let pThis = this;
        this.form.submit(e => {
            pThis._submit(e);
        })
    }

    _loadFailed() {
        this.wrapper.html('<div class="alert alert-danger">An error occurred while displaying the dialog!</div>');
    }

    _submit(e) {
        let pThis = this;
        let url = this.form.attr('action');
        let ajax_settings = {
            url,
        };

        if (this.form.attr('enctype') === 'multipart/form-data') {
            ajax_settings.data = new FormData(this.form[0]);
            ajax_settings.contentType = false;
            ajax_settings.processData = false;
            ajax_settings.cache = false;
        }
        else {
            ajax_settings.data = this.form.serialize();
        }

        $.post(ajax_settings)
            .done(result => {
                pThis._submitDone(result);
            })
            .fail(() => {
                pThis._submitFailed();
            })
            .always(() => {
                pThis.modalLoadingRing.fadeOut(100);
                pThis.wrapper.find(":input").prop("disabled", false);
            });

        this.modalLoadingRing.fadeIn(200);
        this.wrapper.find(":input").prop("disabled", true);

        e.preventDefault();
    }

    _submitDone(result) {
        // Clear old errors first
        this.form.find('.modal-field-error').remove();

        if (!result.hasOwnProperty('success')) {
            this._submitInvalidResponse();
            return;
        }

        if (result.success) {
            this._hideModal();
            if (this.submitCallback !== null)
                this.submitCallback();
        }
        else {
            if (!result.hasOwnProperty('errors')) {
                this._submitInvalidResponse();
                return;
            }

            for (let field in result.errors)
                if (result.errors.hasOwnProperty(field))
                {
                    let errorsArray = result.errors[field];
                    let errorsConcat = "<div class=\"alert alert-danger modal-field-error\"><ul>";

                    for(let error of errorsArray) {
                        errorsConcat += `<li>${error.message}</li>`;
                    }
                    errorsConcat += '</ul></div>';

                    if (field === '__all__')
                        this.form.find('.modal-body').append(errorsConcat);
                    else
                        this.form.find(`[name='${field}']`).after(errorsConcat);
                }

            let errorsHtml = '';

            let err = this.modal.find('#__modal_error');
            if (err.length) {
                err.html('An error occurred');
            }
            else {
                this.modal.find('.modal-body').append(errorsHtml)
            }
        }
    }

    _submitFailed() {
        // Clear old errors first
        this.form.find('.modal-field-error').remove();
        this.form.find('.modal-body')
            .append(`<div class="alert alert-danger modal-field-error">An error occurred while processing request!</div>`);
    }

    _submitInvalidResponse() {
        // Clear old errors first
        this.form.find('.modal-field-error').remove();
        this.form.find('.modal-body')
            .append(`<div class="alert alert-danger modal-field-error">Invalid server response!</div>`);
    }

    loadAndShow()
    {
        let pThis = this;
        this._showLoading();

        $.get(this.url)
            .done(result => {
                pThis._load(result);
                pThis._showModal();
            })
            .fail(() => {
                pThis._loadFailed();
            })
            .always(() => {
                pThis._hideLoading();
            });
    }
}

function syncNow() {
    $.post("{% url 'ajax_action_sync_now' %}", {
        csrfmiddlewaretoken: '{{ csrf_token }}'
    });
}

function ajaxLink_Clicked() {
    let url_post = $(this).data('post-url');
    let url_get = $(this).data('get-url');

    if (url_post !== null) {
        $.post(url_post, {
            csrfmiddlewaretoken: '{{ csrf_token }}'
        });
    }
    else if (url_get !== null) {
        $.get(url_get, {
            csrfmiddlewaretoken: '{{ csrf_token }}'
        });
    }
    return false;
}

///
/// Initialization
///
$(document).ready(() => {
    $(".ajax-link").on("click", ajaxLink_Clicked);
    $("#btn_sync_now").on("click", syncNow);
});
