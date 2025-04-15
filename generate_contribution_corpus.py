import os
import requests
import pandas as pd
import argparse
from pathlib import Path
from xml.dom import minidom
from typing import List, Dict, Any, Optional

# Panel member PIDs - grouped by panel
PANEL_MEMBERS = {
    "LABOUR": [
        "#JerryButtimer", "#PatCasey", "#ShaneCassells", "#GerardPCraughwell",
        "#JohnCummins", "#RobbieGallagher", "#PaulGavan", "#JoeOReilly",
        "#PaulineOReilly", "#NedOSullivan", "#MarieSherlock", "#ChrisAndrews",
        "#NessaCosgrove", "#MarkDuffy", "#MikeKennelly", "#MariaMcCormack",
        "#MargaretMurphyOMahony", "#PatriciaStephenson", "#MáireDevine",
        "#TerryLeyden", "#JenniferMurnaneOConnor", "#GedNash", "#NealeRichmond"
    ],
    "NUI": [
        "#AliceMaryHiggins", "#MichaelMcDowell", "#RónánMullen", 
        "#JohnCrown", "#FeargalQuinn"
    ]
}

# Party affiliations
PARTY_AFFILIATIONS = {
    "FINE_GAEL": ["#JerryButtimer", "#JohnCummins", "#JoeOReilly", "#NealeRichmond"],
    "FIANNA_FAIL": ["#PatCasey", "#NedOSullivan", "#TerryLeyden", "#JenniferMurnaneOConnor"],
    "LABOUR": ["#PaulGavan", "#MarieSherlock", "#GedNash", "#MáireDevine"],
    "SINN_FEIN": ["#ChrisAndrews"],
    "INDEPENDENT": [
        "#GerardPCraughwell", "#MichaelMcDowell", "#RónánMullen", 
        "#JohnCrown", "#FeargalQuinn", "#AliceMaryHiggins"
    ]
}

# Valid house numbers
VALID_HOUSE_NUMBERS = ["24", "25", "26"]

# API configuration
API_BASE_URL = "https://api.oireachtas.ie/v1"
DEFAULT_START_DATE = "2011-01-01"
DEFAULT_END_DATE = "2023-12-31"
DEFAULT_LIMIT = 1300


def get_panel_members(panel_name: str, date_start: str) -> List[Dict[str, str]]:
    endpoint = f"{API_BASE_URL}/members"
    params = {
        "chamber_id": "seanad",
        "date_start": date_start,
        "panel_id": panel_name.lower(),
        "limit": 100
    }
    
    response = requests.get(endpoint, params=params, verify=False)
    if response.status_code != 200:
        print(f"Error fetching panel members: {response.status_code}")
        return []
        
    members = []
    try:
        data = response.json()
        for member in data.get('results', []):
            member_data = member.get('member', {})
            membership_data = member_data.get("memberships", [{}])[0]
            parties_data = membership_data.get("membership", {}).get("parties", [{}])[0]
            party_code = parties_data.get("party", {}).get("partyCode", "Unknown")
            
            members.append({
                'member_id': member_data.get('memberCode', ''),
                'full_name': member_data.get('fullName', ''),
                'party_code': party_code
            })
    except Exception as e:
        print(f"Error parsing member data: {e}")
        
    return members


def get_speaker_details(speech_element, panel_members: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
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


def determine_panel_name(speaker_pid: str) -> Optional[str]:
    if speaker_pid in PANEL_MEMBERS["LABOUR"]:
        return "Labour Panel"
    elif speaker_pid in PANEL_MEMBERS["NUI"]:
        return "NUI"
    return None


def determine_party_name(speaker_pid: str) -> str:
    for party, members in PARTY_AFFILIATIONS.items():
        if speaker_pid in members:
            if party == "FINE_GAEL":
                return "Fine Gael"
            elif party == "FIANNA_FAIL":
                return "Fianna Fáil"
            elif party == "LABOUR":
                return "Labour"
            elif party == "SINN_FEIN":
                return "Sinn Féin"
            elif party == "INDEPENDENT":
                return "Independent"
    return "University"  # Default for unidentified members


def extract_contribution_text(speech_element) -> str:
    contribution = ""
    paragraphs = speech_element.getElementsByTagName('p')
    for paragraph in paragraphs:
        if paragraph.firstChild and getattr(paragraph.firstChild, 'data', None):
            contribution += paragraph.firstChild.data + " "
    return contribution.strip()


def parse_debate_XML(url: str, panel_members: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    debate_records = []

    response = requests.get(url, verify=False)
    if response.status_code != 200:
        print(f"Error fetching data from API: {url}")
        return []

    try:
        xml_debate = minidom.parseString(response.content)
    except Exception as e:
        print(f"Error parsing XML content: {e}")
        return []

    # Get house information
    try:
        author_elements = xml_debate.getElementsByTagName('FRBRWork')[0].getElementsByTagName('FRBRauthor')[0]
        house = author_elements.getAttribute('href')
        house_code = Path(house).parts[-2]
        house_number = Path(house).parts[-1]
        
        # Get debate date
        debate_date = xml_debate.getElementsByTagName('docDate')[0].getAttribute('date')
    except (IndexError, AttributeError) as e:
        print(f"Error extracting basic debate information: {e}")
        return []

    # Skip debates from houses not in our valid list
    if house_number not in VALID_HOUSE_NUMBERS:
        return []

    # Process debate sections
    debate_sections = xml_debate.getElementsByTagName('debateSection')
    for debate_section in debate_sections:
        try:
            section_id = debate_section.attributes['eId'].value
            
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
                try:
                    # Get speaker details
                    speaker_info = get_speaker_details(speech, panel_members)
                    
                    # Determine panel name
                    panel_name = determine_panel_name(speaker_info['pid'])
                    if not panel_name:
                        continue  # Skip if not in either panel
                    
                    # Determine party name based on PID
                    party_name = determine_party_name(speaker_info['pid'])
                    
                    # Extract contribution text
                    contribution = extract_contribution_text(speech)
                    if not contribution:
                        continue  # Skip empty contributions
                    
                    # Create and append record
                    new_record = {
                        'name': speaker_info['name'],
                        'party': party_name,
                        'panel': panel_name,
                        'pid': speaker_info['pid'],
                        'date': debate_date,
                        'house_code': house_code,
                        'house_no': house_number,
                        'debate_section_topic': topic,
                        'debate_section_id': section_id,
                        'contribution': contribution,
                        'language': 'English',
                        'ordinal_position': len(debate_records) + 1,
                        'order_in_discourse': speech.attributes['eId'].value
                    }
                    debate_records.append(new_record)
                except Exception as e:
                    print(f"Error processing speech: {e}")
                    continue
        except Exception as e:
            print(f"Error processing debate section: {e}")
            continue

    return debate_records


def get_debate_records(chamber: str = "dail", 
                       date_start: str = DEFAULT_START_DATE, 
                       date_end: str = DEFAULT_END_DATE, 
                       limit: int = DEFAULT_LIMIT) -> List[str]:
    endpoint = f"{API_BASE_URL}/debates"
    params = {
        "chamber_type": "house",
        "chamber": chamber.lower(),
        "date_start": date_start,
        "date_end": date_end,
        "limit": limit
    }

    response = requests.get(endpoint, params=params, verify=False)
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


def save_to_file(records: List[Dict[str, Any]], chamber: str, panel: Optional[str], 
                 date_start: str, date_end: str, limit: int) -> None:

    if not records:
        print("No debate records found matching the criteria")
        return
        
    if not os.path.exists("data"):
        os.makedirs("data")

    # Generate filename based on parameters
    panel_str = f"_{panel}_panel" if panel else ""
    date_range = f"{date_start}_to_{date_end}"
    filename = f"data/{chamber}{panel_str}_{date_range}_limit{limit}.tsv"

    df = pd.DataFrame(records)
    df.to_csv(filename, sep='\t', index=False)
    print(f"Saved {len(records)} records to {filename}")


def main():
    # Main function to parse arguments and run the program
    parser = argparse.ArgumentParser(description='Fetch debate records for a chamber panel.')
    parser.add_argument('--chamber', type=str, choices=['dail', 'seanad'], default='seanad',
                      help='Chamber to fetch debates from (dail or seanad)')
    parser.add_argument('--panel', type=str, 
                      choices=['labour', 'agricultural', 'cultural', 'industrial', 'administrative', 'university'],
                      help='Seanad panel to filter by')
    parser.add_argument('--date-start', type=str, default=DEFAULT_START_DATE,
                      help='Start date for debates (YYYY-MM-DD)')
    parser.add_argument('--date-end', type=str, default=DEFAULT_END_DATE,
                      help='End date for debates (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                      help='Limit results (final no. of records could be lower after removing duplicates)')

    args = parser.parse_args()

    # Get panel members if panel specified
    panel_members = None
    if args.panel:
        print(f"Fetching {args.panel.title()} Panel members...")
        panel_members = get_panel_members(args.panel, DEFAULT_START_DATE)
        if not panel_members:
            print(f"No members found for {args.panel.title()} Panel")
            exit(1)
        print(f"Found {len(panel_members)} panel members")

    print(f"Fetching debate records...")
    xml_files = get_debate_records(
        chamber=args.chamber,
        date_start=args.date_start,
        date_end=args.date_end,
        limit=args.limit
    )

    print(f"Processing {len(xml_files)} debate records...")
    all_debate_records = []
    for xml_file in xml_files:
        records = parse_debate_XML(xml_file, panel_members)
        if records:
            all_debate_records.extend(records)

    save_to_file(
        all_debate_records, 
        args.chamber, 
        args.panel,
        args.date_start, 
        args.date_end, 
        args.limit
    )


if __name__ == "__main__":
    main()
