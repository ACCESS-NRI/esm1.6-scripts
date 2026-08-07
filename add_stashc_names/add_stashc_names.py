import argparse
import mule
import re

from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        prog="add_stashc_names",
        description="Add a comment with the variable long name next to each STASH request in a STASHC file."
    )

    parser.add_argument("--STASHmaster",
                        type=Path,
                        help="Path to STASHmaster file containing variable names.",
                        required=True
                        )

    parser.add_argument("input",
                        type=Path,
                        help="Path to input STASHC file."
                      )
    parser.add_argument("output",
                        type=Path,
                        help="Path for writing output STASHC file."
                        )

    return parser.parse_args()


# Various regex patterns for matching lines in the STASHC file
request_pattern = r"\s*&STREQ\s.*?/"
imod_pattern = r"IMOD\s*=\s*\d+"
isec_pattern = r"ISEC\s*=\s*(?P<section>\d+)"
item_pattern = r"ITEM\s*=\s*(?P<item>\d+)"
itim_pattern = r"ITIM\s*=\s*\d+"
idom_pattern = r"IDOM\s*=\s*\d+"
iuse_pattern = r"IUSE\s*=\s*\d+"


def is_stash_request(line):
    """"
    Identify whether a line is a STASH request
    """

    # Options within a stash request can appear in different orders. Search for
    # each component separately
    return (re.match(request_pattern, line) and re.search(imod_pattern, line) and
            re.search(item_pattern, line) and re.search(itim_pattern, line) and
            re.search(idom_pattern, line) and re.search(iuse_pattern, line))


def add_name(line, stashmaster):
    """
    Add a comment with the variable long name at the end of a stash request line
    """
    section = int(re.search(isec_pattern, line)["section"])
    item = int(re.search(item_pattern, line)["item"])
    stashcode = f"{section:02d}{item:03d}"
    request = re.match(request_pattern, line).group() # ignore everything after the "/"
    return request + f"\t! {stashmaster[stashcode].name}\n"


def is_time_def(line):
    return re.match(r"\s*&TIME\s", line)

def is_domain_def(line):
    return re.match(r"\s*&DOMAIN\s", line)

def is_use_def(line):
    return re.match(r"\s*&USE\s", line)

def is_section_start(line):
    return re.match(r"\s*&STASHNUM\s", line)

def is_count_comment(line):
    return re.match(r"! (Time|Domain|Usage) profile number", line)


if __name__ == "__main__":
    args = parse_args()
    stashmaster = mule.STASHmaster.from_file(args.STASHmaster)

    with open(args.input, "r") as STASHC_input:
        lines = STASHC_input.readlines()

    lines_to_write = []
    time_count = 0
    domain_count = 0
    use_count = 0

    for line in lines:
        if is_count_comment(line):
            # Skip existing count comments to avoid duplication
            continue
        if is_stash_request(line):
            line = add_name(line, stashmaster)
        elif is_time_def(line):
            time_count += 1
            lines_to_write.append(f"! Time profile number {time_count}\n")
        elif is_domain_def(line):
            domain_count += 1
            lines_to_write.append(f"! Domain profile number {domain_count}\n")
        elif is_use_def(line):
            use_count += 1
            lines_to_write.append(f"! Usage profile number {use_count}\n")
        elif is_section_start(line):
            # Reset the time, domain, and profile counts for new sections of the file
            time_count = 0
            domain_count = 0
            use_count = 0

        lines_to_write.append(line)

    with open(args.output, "w") as STASHC_output:
        STASHC_output.writelines(lines_to_write)
