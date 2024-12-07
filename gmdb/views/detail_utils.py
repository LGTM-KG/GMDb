from gmdb.views.detail_queries import GROUPED_VARS_FLAT, GROUPED_VARS


def add_infobox_link(label, url, icon=None, infobox_links=[]):
    if not url:
        return

    data_to_add = {
        'label': label,
        'url': url,
        'icon': icon if icon else 'fa6-solid:globe'
    }

    infobox_links.append(data_to_add)


def add_streaming_data(label, urls, icon=None, color=None, theme=None, streaming_data={}):
    if not urls:
        return

    data_to_add = {
        'label': label,
        'urls': urls,
        'icon': icon if icon else 'fa6-solid:globe',
        'color': color if color else '',
        'theme': theme if theme else 'dark'
    }

    streaming_data.append(data_to_add)


def to_infobox_list(key, label_key, url_key=None, img_key=None, result_data={}):
    if key not in result_data:
        return []
    infobox_list_data = []
    for item in result_data[key]:
        item_data = result_data[key][item]
        data_to_add = {}
        data_to_add['id'] = item_data[key]
        data_to_add['label'] = item_data[label_key]
        if url_key and item_data.get(url_key):
            data_to_add['url'] = item_data[url_key]
        if img_key and item_data.get(img_key):
            data_to_add['img'] = item_data[img_key]
        infobox_list_data.append(data_to_add)
    return infobox_list_data


def extract_and_group_results(result, result_data, query_result):
    for row in query_result['results']['bindings']:
        if result is None:
            result = {}

        pending_value_group = {}

        for key, value in row.items():
            value_str = value['value'] if value else None
            key_str = key

            if not key_str in result:
                result[key_str] = value_str

            # find group_var that has key_str
            group_var = next((group_var for group_var in GROUPED_VARS if key_str in group_var), None)

            if group_var:
                if group_var not in pending_value_group:
                    pending_value_group[group_var] = {}
                pending_value_group[group_var][key_str] = value_str
            else:
                if value_str not in result_data[key_str]:
                    result_data[key_str].append(value_str)

        for group_var, group_value in pending_value_group.items():
            group_var_key = group_var[0]
            group_value_key = group_value[group_var_key]

            if group_var_key not in result_data:
                result_data[group_var_key] = dict()

            if group_value_key not in result_data[group_var_key]:
                result_data[group_var_key][group_value_key] = group_value
    return result


def initialize_result_data(result_data, query_2_result):
    for var in query_2_result['head']['vars']:
        var_str = var
        if var_str in result_data:
            continue
        if var_str in GROUPED_VARS_FLAT:
            continue
        result_data[var_str] = []
