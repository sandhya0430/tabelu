import tableauserverclient as TSC

def get_tableau_server(tableau_details):
    tableau_auth = TSC.TableauAuth(**tableau_details['credentials'])
    server = TSC.Server(tableau_details['server'])
    server.version = tableau_details['api_version']
    server.auth.sign_in(tableau_auth)
    return server
def get_workbook_by_name(server, wb_name):
    req_option = TSC.RequestOptions()
    req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.Name, 
                                     TSC.RequestOptions.Operator.Equals, 
                                     wb_name))
    matching_workbooks, _ = server.workbooks.get(req_option)
    return matching_workbooks[0]
def download_workbook_by_name(tableau_details, file_path, wb_name):
    server = get_tableau_server(tableau_details)
    wb =  get_workbook_by_name(server, wb_name)
    wb_file_path = server.workbooks.download(wb.id, filepath=file_path, include_extract=False)
    return wb_file_path
