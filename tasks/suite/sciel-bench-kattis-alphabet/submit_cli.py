"""Command-line entry point for the bundled Kattis submission helper."""
from submit import (
    ConfigError,
    argparse,
    configparser,
    confirm_or_die,
    get_config,
    get_submission_url,
    get_url,
    guess_language,
    guess_mainclass,
    login_from_config,
    os,
    requests,
    show_judgement,
    submit,
    sys,
)

def main():
    parser = argparse.ArgumentParser(prog="kattis", description="Submit a solution to Kattis")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-a",
        "--assignment",
        help="""Short name of assignment you want to submit to
Overrides default guess (server guesses based on assignments you are in)""",
    )
    group.add_argument(
        "-c",
        "--contest",
        help="""Short name of contest you want to submit to
Overrides default guess (server guesses based on contests you are in)""",
    )
    parser.add_argument(
        "-p",
        "--problem",
        help="""'Which problem to submit to.
Overrides default guess (first part of first filename)""",
    )
    parser.add_argument(
        "-m",
        "--mainclass",
        help="""Sets mainclass.
Overrides default guess (first part of first filename)""",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="""Sets language.
Overrides default guess (based on suffix of first filename)""",
    )
    parser.add_argument("-t", "--tag", help=argparse.SUPPRESS)
    parser.add_argument(
        "-f", "--force", help="Force, no confirmation prompt before submission", action="store_true"
    )
    parser.add_argument("files", nargs="+")

    args = parser.parse_args()
    files = args.files

    try:
        cfg = get_config()
    except ConfigError as exc:
        print(exc)
        sys.exit(1)

    problem, ext = os.path.splitext(os.path.basename(files[0]))
    language = guess_language(ext, files)
    mainclass = guess_mainclass(language, files)
    tag = args.tag

    problem = problem.lower()

    if args.problem:
        problem = args.problem

    if args.mainclass is not None:
        mainclass = args.mainclass

    if args.language:
        language = args.language

    if language is None:
        print(f'''\
No language specified, and I failed to guess language from filename
extension "{ext}"''')
        sys.exit(1)

    files = sorted(list(set(args.files)))

    try:
        login_reply = login_from_config(cfg)
    except ConfigError as exc:
        print(exc)
        sys.exit(1)
    except requests.exceptions.RequestException as err:
        print("Login connection failed:", err)
        sys.exit(1)

    if not login_reply.status_code == 200:
        print("Login failed.")
        if login_reply.status_code == 403:
            print("Incorrect username or password/token (403)")
        elif login_reply.status_code == 404:
            print("Incorrect login URL (404)")
        else:
            print("Status code:", login_reply.status_code)
        sys.exit(1)

    submit_url = get_url(cfg, "submissionurl", "submit")

    if not args.force:
        confirm_or_die(problem, language, files, mainclass, tag)

    try:
        result = submit(
            submit_url,
            login_reply.cookies,
            problem,
            language,
            files,
            mainclass,
            tag,
            args.assignment,
            args.contest,
        )
    except requests.exceptions.RequestException as err:
        print("Submit connection failed:", err)
        sys.exit(1)

    if result.status_code != 200:
        print("Submission failed.")
        if result.status_code == 403:
            print("Access denied (403)")
        elif result.status_code == 404:
            print("Incorrect submit URL (404)")
        else:
            print("Status code:", result.status_code)
        sys.exit(1)

    plain_result = result.content.decode("utf-8").replace("<br />", "\n")
    print(plain_result)

    submission_url = None
    try:
        submission_url = get_submission_url(plain_result, cfg)
    except configparser.NoOptionError:
        pass

    if submission_url:
        _, score, testcases_done, testcases_correct, testcases_total = show_judgement(
            submission_url, cfg
        )
        print(f"Score: {score}")
        print(f"Test cases done: {testcases_done}")
        print(f"Test cases correct: {testcases_correct}")
        print(f"Test cases total: {testcases_total}")
