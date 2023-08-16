"""A helper module for integrating Excel data into the project"""
import pandas as pd
import json


def excel_to_params_json():
    # Read Excel data
    df = pd.read_excel(r'C:\Users\emine\PycharmProjects\Article-Search\col_md12.xlsx', header=None)

    # Initialize empty list to store the data
    data_list = []

    # Iterate over DataFrame rows
    for index, row in df.iterrows():
        # Get the elements of each row
        data1, data2 = row

        # Perform your journal_name logic
        journal_name = data1.strip()
        journal_name = journal_name.split()
        str_f = "_"
        objects_list = []
        for element in journal_name:
            objects_list.append(element.lower().encode(encoding="ascii", errors="ignore").decode(encoding="UTF-8"))

        # Create a formatted string using objects_list and index
        last_element = str(index + 1) + str_f + "".join(objects_list)

        # Append to the main list
        data_list.append([data1.strip(), data2, "col_md12", 1, "thursday_1-11_col_md12", last_element])

    # Convert list to JSON and write it to a file
    with open('../../../dispatchers/col_md12/col_md12_1-11/1-11_col_md12_params.json', 'w', encoding='utf-8') as f:
        json.dump(data_list, f, indent=4, ensure_ascii=False)


def read_data_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def journal_name_to_ascii(journal_name: str) -> str:
    journal_name = journal_name.strip()
    journal_name = journal_name.split()
    str_f = "_"
    objects_list = []

    for element in journal_name:
        objects_list.append(element.lower().encode(encoding="ascii", errors="ignore").decode(encoding="UTF-8"))

    return str_f.join(objects_list)


if __name__ == "__main__":
    excel_to_params_json()
    # file_path = r'C:\Users\emine\PycharmProjects\Article-Search\common\helpers\methods\dergipark_81-160_params.json'  # replace with your file path
    # data_list = read_data_from_json(file_path)
    #
    # # print the data to see if it's correctly loaded
    # for item in data_list:
    #     print(item)