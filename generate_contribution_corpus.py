import os
from datetime import datetime
import requests
import pandas as pd
from pathlib import Path
from xml.dom import minidom
import argparse

from scipy.stats import mannwhitneyu

            # PIDs of Labour Panel
            Labour_names = [
                "#JerryButtimer", "#PatCasey", "#ShaneCassells", "#GerardPCraughwell",
                "#JohnCummins", "#RobbieGallagher", "#PaulGavan", "#JoeOReilly",
                "#PaulineOReilly", "#NedOSullivan", "#MarieSherlock", "#ChrisAndrews",
                "#NessaCosgrove", "#MarkDuffy", "#MikeKennelly", "#MariaMcCormack",
                "#MargaretMurphyOMahony", "#PatriciaStephenson", "#MáireDevine",
                "#TerryLeyden", "#JenniferMurnaneOConnor", "#GedNash", "#NealeRichmond",
                
            ]
            # PIDs of NUI panel
            NUI_names = [
                "#AliceMaryHiggins", "#MichaelMcDowell", "#RónánMullen", "#JohnCrown", "#FeargalQuinn"
            ]

            # Fine Gael Members
            Fine_Gael_Members = [
                "#JerryButtimer", "#JohnCummins", "#JoeOReilly", "#NealeRichmond"
            ]

            # Fianna Fáil Members
            Fianna_Fáil_Members = [
                "#PatCasey", "#NedOSullivan", "#TerryLeyden", "#JenniferMurnaneOConnor"
            ]   

            # Labour Party Members
            Labour_Members = [
                "#PaulGavan", "#MarieSherlock", "#GedNash", "#MáireDevine"
            ]

            # Sinn Féin Members
            Sinn_Féin_Members = [
                "#ChrisAndrews"
            ]

            # Independent Members
            Independent_Members = [
                "#GerardPCraughwell", "#MichaelMcDowell", "#RónánMullen", "#JohnCrown", "#FeargalQuinn", "#AliceMaryHiggins"
            ]

def run_statistical_tests(labour, nui):
    print("\n=== Mann-Whitney U Test Results ===")

    metrics = {
        "TTR": (labour.TTR, nui.TTR),
        "Word Length": (labour.word_length, nui.word_length),
        "Complex T-unit Ratio": (labour.complex_tunit_ratio, nui.complex_tunit_ratio),
        "Sentence Length": (labour.sentence_length, nui.sentence_length)
    }

    for metric_name, (labour_data, nui_data) in metrics.items():
        u_stat, p_value = mannwhitneyu(labour_data, nui_data, alternative='two-sided')
        print(f"\nMetric: {metric_name}")
        print(f"U Statistic = {u_stat:.3f}")
        print(f"p-value = {p_value:.4f}")

        if p_value < 0.05:
            print("→ Significant difference between Labour and NUI panels.")
        else:
            print("→ No significant difference between Labour and NUI panels.")


def get_panel_members(panel_name, date_start):
    """Get list of members from a specific Seanad panel"""
    base_url = "https://api.oireachtas.ie/v1/members"
    params = {
        "chamber_id": "seanad",
        "date_start": date_start,
        "panel_id": panel_name.lower(),
        "limit": 100
    }
    
    response = requests.get(base_url, params=params, verify=False)
    if response.status_code != 200:
        print(f"Error fetching panel members: {response.status_code}")
        return []
        
    members = []
    # party = "error"
    try:
        data = response.json()
        for member in data.get('results', []):
            member_data = member.get('member', {})
            members.append({
                'member_id': member_data.get('memberCode', ''),
                'full_name': member_data.get('fullName', ''),
                'party_code': member_data["memberships"][0]["membership"]["parties"][0]["party"]["partyCode"]  # Safely access partyCode
            })
    except Exception as e:
        print(f"Error parsing member data: {e}")
        
    return members


def get_speaker_details(speech_element, panel_members=None):
    """Extract speaker details from speech element"""
    by_attribute = speech_element.attributes['by'].value
    speaker_id = by_attribute[1:] if by_attribute.startswith('#') else by_attribute
    
    # Default values
    speaker_name = speaker_id
    party = "Unknown"
    panel = "Unknown"
    
    # Check if speaker is in panel members
    if panel_members:
        for member in panel_members:
            if member['member_id'].lower() in speaker_id.lower():
                speaker_name = member['full_name']
                party = member['party_code']
                break
    
    # Try to get name from speech element if not found in panel members
    if speaker_name == speaker_id:
        from_elements = speech_element.getElementsByTagName('from')
        if from_elements and from_elements[0].firstChild:
            speaker_name = from_elements[0].firstChild.data.strip()
    
    return {
        'name': speaker_name,
        'party': party,
        'panel': panel,
        'pid': by_attribute
    }


def parse_debate_XML(url, panel_members=None):
    """Parse debate XML and extract speeches"""
    debate_record = []

    response = requests.get(url, verify=False)
    if response.status_code != 200:
        print(f"Error fetching data from API: {url}")
        return []

    current_xml_debate_record = minidom.parseString(response.content)

    # Get house information
    author_elements = current_xml_debate_record.getElementsByTagName('FRBRWork')[0].getElementsByTagName('FRBRauthor')[0]
    house = author_elements.getAttribute('href')
    housecode = Path(house).parts[-2]
    houseno = Path(house).parts[-1]

    # Get debate date
    date = current_xml_debate_record.getElementsByTagName('docDate')[0].getAttribute('date')

    # Process debate sections
    debate_sections = current_xml_debate_record.getElementsByTagName('debateSection')
    for debate_section in debate_sections:
        debate_section_id = debate_section.attributes['eId'].value
        
        # Get topic
        headings = debate_section.getElementsByTagName('heading')
        topic = 'No topic'
        for heading in headings:
            if heading.firstChild:
                topic = heading.firstChild.data
                break

        # Process speeches
        speeches = debate_section.getElementsByTagName('speech')
        for speech in speeches:
            # Get speaker details
            speaker_info = get_speaker_details(speech, panel_members)


            accepted_houses = ["24", "25", "26"]

            # Checks if they are in either panels, setting panel attribute respectively
            # If not, then we skip
            panelName = "Unknown"

            if speaker_info['pid'] in Labour_names:
                panelName = "Labour Panel"
            elif speaker_info['pid'] in NUI_names:
                panelName = "NUI"
            else:
                break
            
            
            # Also, if the house number is further back than 24, we also skip
            if houseno not in accepted_houses:
                break

            # Check and allocates party names based on PID
            if speaker_info['pid'] in Fine_Gael_Members:
                partyName = "Fine Gael"
            elif speaker_info['pid'] in Fianna_Fáil_Members:
                partyName = "Fine Fáil"
            elif speaker_info['pid'] in Labour_Members:
                partyName = "Labour"
            elif speaker_info['pid'] in Sinn_Féin_Members:
                partyName = "Sinn Féin"
            elif speaker_info['pid'] in Independent_Members:
                partyName = "Independant"
            else:
                partyName = "University"
            
            
            # Extract contribution
            contribution = ""
            paragraphs = speech.getElementsByTagName('p')
            for paragraph in paragraphs:
                if paragraph.firstChild and getattr(paragraph.firstChild, 'data', None):
                    contribution += paragraph.firstChild.data + " "

            if contribution.strip():  # Only add non-empty contributions
                new_row = {
                    'name': speaker_info['name'],
                    'party': partyName,
                    'panel': panelName,
                    'pid': speaker_info['pid'],
                    'date': date,
                    'house_code': housecode,
                    'house_no': houseno,
                    'debate_section_topic': topic,
                    'debate_section_id': debate_section_id,
                    'contribution': contribution.strip(),
                    'language': 'English',
                    'ordinal_position': len(debate_record) + 1,
                    'order_in_discourse': speech.attributes['eId'].value
                }
                debate_record.append(new_row)

    return debate_record


def get_debate_records(chamber="dail", date_start="1900-01-01", date_end="2099-01-01", limit=50):
    """Get debate records with optional filtering by chamber and date range"""
    base_url = "https://api.oireachtas.ie/v1/debates"
    params = {
        "chamber_type": "house",
        "chamber": chamber.lower(),
        "date_start": date_start,
        "date_end": date_end,
        "limit": limit
    }

    response = requests.get(base_url, params=params, verify=False)
    if response.status_code != 200:
        print(f"Error fetching data from API: {response.status_code}")
        return []

    json_response = response.json()
    xml_files = []
    
    results = json_response.get('results', [])
    for result in results:
        if 'debateRecord' not in result:
            continue
        formats = result['debateRecord'].get('formats', {})
        xml_uri = formats.get('xml', {}).get('uri')
        if xml_uri and xml_uri not in xml_files:
            xml_files.append(xml_uri)

    return xml_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch debate records for a chamber panel.')
    parser.add_argument('--chamber', type=str, choices=['dail', 'seanad'], default='seanad',
                        help='Chamber to fetch debates from (dail or seanad)')
    parser.add_argument('--panel', type=str, choices=['labour', 'agricultural', 'cultural', 'industrial', 'administrative', 'university'],
                        help='Seanad panel to filter by')
    # Changed debate year default back to 2011 cuz thats when the 24th seanad started
    parser.add_argument('--date-start', type=str, default='2011-01-01',
                        help='Start date for debates (YYYY-MM-DD)')
    parser.add_argument('--date-end', type=str, default='2023-12-31',
                        help='End date for debates (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=1300,
                        help='Limit results (final no. of records could be lower after removing duplicates)')

    args = parser.parse_args()

    # Get panel members if panel specified
    panel_members = None
    if args.panel:
        print(f"Fetching {args.panel.title()} Panel members...")
        panel_members = get_panel_members(args.panel, '2011-01-01')
        if not panel_members:
            print(f"No members found for {args.panel.title()} Panel")
            exit(1)
        print(f"Found {len(panel_members)} panel members")

    print(f"Fetching debate records...")
    debate_records = []
    xml_files = get_debate_records(
        chamber=args.chamber,
        date_start=args.date_start,
        date_end=args.date_end,
        limit=args.limit
    )

    print(f"Processing {len(xml_files)} debate records...")
    for xml_file in xml_files:
        debate_record = parse_debate_XML(xml_file, panel_members)
        if debate_record:
            debate_records.extend(debate_record)

    if debate_records:
        if not os.path.exists("data"):
            os.makedirs("data")

        # Generate filename based on parameters
        panel_str = f"_{args.panel}_panel" if args.panel else ""
        date_range = f"{args.date_start}_to_{args.date_end}"
        filename = f"data/{args.chamber}{panel_str}_{date_range}_limit{args.limit}.tsv"

        df = pd.DataFrame(debate_records)
        df.to_csv(filename, sep='\t', index=False)
        print(f"Saved {len(debate_records)} records to {filename}")
    else:
        print("No debate records found matching the criteria")
