/*
 * Drop in replacement for country -> US State dropdown in the case the
 * country is United States.
 */
if ( window['innershed'] === undefined ) innershed = {};


/*
 * Replace given input field for county with a drop down box for selecting
 * US States instead if the given country is United States.
 */
innershed.USStates = function(country, county, postcode) {
    this._country = country;
    this._county = county;
    this._isCountyRequired = false;
    this._postcode = postcode;

    // identify fields by typical name
    if (!this._country || this._country.length === 0) this._country = $('#id_country');
    if (!this._county || this._county.length === 0) this._county = $('#id_county');
    if (!this._postcode || this._postcode.length === 0) this._postcode = $('#id_postcode');

    this._countyId = this._county.attr('id');
    this._countyName = this._county.attr('name');

    this._bound = {
        onCountryChanged: $.proxy(this.onCountryChanged, this)
    };

    // changing country should switch fields
    this._country.bind('change', this._bound.onCountryChanged);
    this.updateUIState();
};


innershed.USStates.prototype = {
    REPLACED_NAME: 'innershed-replaced-by-us-states',


    US_STATES: [
        { 'iso': 'AL', 'title': 'Alabama' },
        { 'iso': 'AK', 'title': 'Alaska' },
        { 'iso': 'AZ', 'title': 'Arizona' },
        { 'iso': 'AR', 'title': 'Arkansas' },
        { 'iso': 'CA', 'title': 'California' },
        { 'iso': 'CO', 'title': 'Colorado' },
        { 'iso': 'CT', 'title': 'Connecticut' },
        { 'iso': 'DE', 'title': 'Delaware' },
        { 'iso': 'FL', 'title': 'Florida' },
        { 'iso': 'GA', 'title': 'Georgia' },
        { 'iso': 'HI', 'title': 'Hawaii' },
        { 'iso': 'ID', 'title': 'Idaho' },
        { 'iso': 'IL', 'title': 'Illinois' },
        { 'iso': 'IN', 'title': 'Indiana' },
        { 'iso': 'IA', 'title': 'Iowa' },
        { 'iso': 'KS', 'title': 'Kansas' },
        { 'iso': 'KY', 'title': 'Kentucky' },
        { 'iso': 'LA', 'title': 'Louisiana' },
        { 'iso': 'ME', 'title': 'Maine' },
        { 'iso': 'MD', 'title': 'Maryland' },
        { 'iso': 'MA', 'title': 'Massachusetts' },
        { 'iso': 'MI', 'title': 'Michigan' },
        { 'iso': 'MN', 'title': 'Minnesota' },
        { 'iso': 'MS', 'title': 'Mississippi' },
        { 'iso': 'MO', 'title': 'Missouri' },
        { 'iso': 'MT', 'title': 'Montana' },
        { 'iso': 'NE', 'title': 'Nebraska' },
        { 'iso': 'NV', 'title': 'Nevada' },
        { 'iso': 'NH', 'title': 'New Hampshire' },
        { 'iso': 'NJ', 'title': 'New Jersey' },
        { 'iso': 'NM', 'title': 'New Mexico' },
        { 'iso': 'NY', 'title': 'New York' },
        { 'iso': 'NC', 'title': 'North Carolina' },
        { 'iso': 'ND', 'title': 'North Dakota' },
        { 'iso': 'OH', 'title': 'Ohio' },
        { 'iso': 'OK', 'title': 'Oklahoma' },
        { 'iso': 'OR', 'title': 'Oregon' },
        { 'iso': 'PA', 'title': 'Pennsylvania' },
        { 'iso': 'RI', 'title': 'Rhode Island' },
        { 'iso': 'SC', 'title': 'South Carolina' },
        { 'iso': 'SD', 'title': 'South Dakota' },
        { 'iso': 'TN', 'title': 'Tennessee' },
        { 'iso': 'TX', 'title': 'Texas' },
        { 'iso': 'UT', 'title': 'Utah' },
        { 'iso': 'VT', 'title': 'Vermont' },
        { 'iso': 'VA', 'title': 'Virginia' },
        { 'iso': 'WA', 'title': 'Washington' },
        { 'iso': 'WV', 'title': 'West Virginia' },
        { 'iso': 'WI', 'title': 'Wisconsin' },
        { 'iso': 'WY', 'title': 'Wyoming' }
    ],


    dispose: function() {
        this._country.bind('change', this._bound.onCountryChanged);
        this._bound = null;
        this._country = null;
        this._county = null;
    },


    /*
     * Event handler for handling changes of the country.
     */
    onCountryChanged: function(e) {
        this.updateUIState();
    },


    /*
     * Update UI state depending on the currently selected country.
     */
    updateUIState: function() {
        if ( this._country.val() === 'US' ) {
            this.enableUSStates();
        } else {
            this.disableUSStates();
        }
    },


    /*
     * Return True, if USStates drop down is enabled.
     */
    isUSStatesEnabled: function() {
        return this._county.hasClass(this.REPLACED_NAME);
    },


    /*
     * Enable US States drop down
     */
    enableUSStates: function() {
        if ( this.isUSStatesEnabled() ) return;

        this.hideOriginalCounty();
        this._usstates = this.createUSDropDown();

        this.updateLabel(this._usstates, 'State', 'County');
        this.updateLabel(this._postcode, 'ZIP', 'Postcode');
    },


    /*
     * Disable US States drop down
     */
    disableUSStates: function() {
        if ( !this.isUSStatesEnabled() ) return;

        this.showOriginalCounty();
        this.updateLabel(this._usstates, 'State', 'County');
        this.updateLabel(this._postcode, 'ZIP', 'Postcode');
        this.destroyUSDropDown();
    },


    /*
     * Find the corresponding label for the given form element, either by
     * id or name assuming that the label is using the for attribute.
     */
    getLabelForField: function(field) {
        if ( !field ) return $();

        // find label by id or name
        var label = $('label[for="' + field.attr('id') + '"');
        if ( label.length === 0 ) label = $('label[for="' + field.attr('name') + '"');

        // we might have different component in there...
        if ( label.find('span').not('.required_indicator').length > 0 ) {
            label = label.find('span').first();
        }

        return label;
    },


    /*
     * Update the form label for the county, which in the case of United States
     * is 'State' rather than 'County'.
     */
    updateLabel: function(field, usLabel, nonUSLabel) {
        var label = this.getLabelForField(field);
        if ( label.length > 0 ) {
            label.text(this.isUSStatesEnabled() ? usLabel : nonUSLabel);
        }
    },


    /*
     * Update the form label for postcode, for United States this is 'ZIP'
     * rather than 'Postcode'.
     */
    updatePostcodeLabel: function() {
    },


    /*
     * Hide original county field and rename id and name attributes
     * (the us states field will take the id and name of the original field).
     */
    hideOriginalCounty: function() {
        this._county.addClass(this.REPLACED_NAME)
        this._county.attr('id', 'id-' + this.REPLACED_NAME);
        this._county.attr('name', this.REPLACED_NAME);
        this._isCountyRequired = this._county.attr('required');
        this._county.attr('required', false);
        this._county.hide();
    },


    /*
     * Restore original county field.
     */
    showOriginalCounty: function() {
        this._county.removeClass(this.REPLACED_NAME)
        this._county.attr('id', this._countyId);
        this._county.attr('name', this._countyName);
        this._county.attr('required', this._isCountyRequired);
        this._county.show();
    },


    /*
     * Create US States drop down and initialize it with the current value
     * from county.
     */
    createUSDropDown: function() {
        var dn = $('<select id="' + this._countyId + '" name="' + this._countyName + '" size="1"></select>');
        for ( var i = 0; i < this.US_STATES.length; i++ ) {
            dn.append($('<option value="' + this.US_STATES[i].iso + '">' + this.US_STATES[i].title + '</option>'));
        }

        dn.val(this._county.val());
        dn.insertAfter(this._county);

        return dn;
    },


    /*
     * Destroy US States drop down.
     */
    destroyUSDropDown: function() {
        this._usstates.remove();
        this._usstates = null;
    }
};
