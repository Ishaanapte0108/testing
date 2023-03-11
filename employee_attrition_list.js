frappe.listview_settings['Employee Attrition'] = {

  onload: function (listview) {

    listview.page.add_menu_item(__('Calculate Attrition'), function () {
      //open up frappe dialogue to get month end date
      var d = new frappe.ui.Dialog({
        title: __('Enter Month End Date'),
        fields: [
          {
            fieldtype: 'Date',
            label: __('Date'),
            fieldname: 'reportingDate'
          }
        ],
        primary_action: function () {
          //fetch entered date
          var values = d.get_values();
          var date = moment(values.reportingDate);
          // var quarterEnd = moment().quarter(moment(values.reportingDate).quarter()).endOf('quarter');
          //check if the date entered is month end date
          var monthEnd = moment().month(moment(values.reportingDate).month()).endOf('month');
          if (date.isSame(quarterEnd, 'day')) {
            frappe.call({
              method: "credence_hr.credence_hr.doctype.employee_attrition.employee_attrition.getEmployeeAttrition",
              args: {
                "reporting_date": values.reportingDate
              },
              callback: function (response) {
                if (response.message == 'Success') {
                  cur_list.refresh()
                }
                else {
                  frappe.throw(__('Something went wrong'));
                }
              }
            });
          }
          else {
            frappe.throw(__('Selected date is not a quarter end date.'));
          }
          d.hide();
        },
        primary_action_label: __('Calculate')
      });
      d.show();
    });
  }
};
