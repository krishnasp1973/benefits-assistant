from flask import Flask, render_template, request, jsonify, session

import os

from eligibility_engine import (

    load_knowledge_base, get_ai_response,

    detect_state, detect_intent, extract_user_profile,

    STATE_URLS, STATE_NAME_TO_CODE

)

from dotenv import load_dotenv



load_dotenv()



app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

knowledge_base = load_knowledge_base()



FPL_2024 = {1:14580, 2:19720, 3:24860, 4:30000, 5:35140, 6:40280, 7:44140, 8:48200}



def calculate_fpl_percent(income, household_size):

    """Returns income as a percentage of Federal Poverty Level."""

    base = FPL_2024.get(household_size, FPL_2024[8] + (household_size - 8) * 4720)

    return round((income / base) * 100)



def get_program_eligibility(income, household_size):

    """Returns which programs the user likely qualifies for based on income."""

    fpl = calculate_fpl_percent(income, household_size)

    results = {"fpl_percent": fpl, "programs": []}



    if fpl <= 138:

        results["programs"].append({

            "name": "Medicaid",

            "status": "likely_qualify",

            "note": f"Your income is {fpl}% FPL — at or below the 138% Medicaid threshold",

            "action": "Apply at healthcare.gov or your state Medicaid office"

        })

    elif fpl <= 200:

        results["programs"].append({

            "name": "ACA Marketplace + Premium Tax Credit",

            "status": "likely_qualify",

            "note": f"Your income is {fpl}% FPL — qualifies for strong subsidies",

            "action": "Apply at healthcare.gov during open enrollment"

        })

        results["programs"].append({

            "name": "Cost Sharing Reductions (Silver Plan)",

            "status": "likely_qualify",

            "note": "At your income level, a Silver plan will have reduced deductibles and copays",

            "action": "Select a Silver plan on healthcare.gov"

        })

    elif fpl <= 400:

        results["programs"].append({

            "name": "ACA Marketplace + Premium Tax Credit",

            "status": "likely_qualify",

            "note": f"Your income is {fpl}% FPL — qualifies for premium tax credits",

            "action": "Apply at healthcare.gov during open enrollment"

        })

    else:

        results["programs"].append({

            "name": "ACA Marketplace (no subsidy)",

            "status": "eligible_no_subsidy",

            "note": f"Your income is {fpl}% FPL — above subsidy threshold but can still buy Marketplace coverage",

            "action": "Compare plans at healthcare.gov"

        })



    return results



@app.route("/")

def index():

    session["conversation_history"] = []

    session["last_topic"] = ""

    session["last_state"] = None

    session["user_profile"] = {

        "state": None, "income": None, "household_size": None,

        "age": None, "life_events": [], "has_insurance": None

    }

    return render_template("index.html")



@app.route("/ask", methods=["POST"])

def ask():

    data = request.get_json()

    user_question = data.get("question", "").strip()



    if not user_question:

        return jsonify({"error": "Please enter a question"}), 400



    conversation_history = session.get("conversation_history", [])

    last_topic = session.get("last_topic", "")

    user_profile = session.get("user_profile", {})



    # Update user profile silently from this message

    user_profile = extract_user_profile(user_question, user_profile)

    session["user_profile"] = user_profile



    # Check intent

    intent = detect_intent(user_question)



    if intent["type"] == "out_of_scope":

        return jsonify({

            "answer": "I specialize in U.S. health insurance benefits — Medicaid, ACA, Medicare, CHIP, VA, and more. Happy to help with any health coverage questions!",

            "sources": [],

            "clarification": None

        })



    if intent["type"] == "abbreviation":

        return jsonify({

            "answer": None,

            "sources": [],

            "clarification": {

                "message": f"Did you mean information about {intent['clarification']}?",

                "expanded_query": intent["expanded_query"],

                "label": intent["clarification"]

            }

        })



    # Detect state

    state_code = detect_state(user_question)

    question_words = user_question.strip().split()

    is_just_state = (

        state_code and

        len(question_words) <= 3 and

        last_topic

    )



    if is_just_state:

        state_name = STATE_URLS[state_code]["name"]

        question_to_ask = f"{last_topic} — specifically for {state_name}"

        session["last_state"] = state_code

    else:

        question_to_ask = user_question

        session["last_topic"] = user_question

        session["last_state"] = state_code



    answer, sources = get_ai_response(

        question_to_ask,

        conversation_history,

        knowledge_base,

        state_code=state_code,

        last_topic=last_topic if is_just_state else None,

        user_profile=user_profile

    )



    conversation_history.append({"role": "user", "content": user_question})

    conversation_history.append({"role": "assistant", "content": answer})

    session["conversation_history"] = conversation_history[-24:]



    # Check if we have enough info to show calculator result

    calculator_result = None

    if user_profile.get("income") and user_profile.get("household_size"):

        calculator_result = get_program_eligibility(

            user_profile["income"],

            user_profile["household_size"]

        )



    return jsonify({

        "answer": answer,

        "sources": sources,

        "clarification": None,

        "state_name": STATE_URLS[state_code]["name"] if state_code else None,

        "calculator_result": calculator_result,

        "user_profile": user_profile

    })



@app.route("/calculate", methods=["POST"])

def calculate():

    """Dedicated endpoint for the income calculator widget."""

    data = request.get_json()

    income = data.get("income")

    household_size = data.get("household_size")



    if not income or not household_size:

        return jsonify({"error": "Please enter both income and household size"}), 400



    try:

        income = int(str(income).replace(",", ""))

        household_size = int(household_size)

    except ValueError:

        return jsonify({"error": "Please enter valid numbers"}), 400



    result = get_program_eligibility(income, household_size)



    # Update user profile

    user_profile = session.get("user_profile", {})

    user_profile["income"] = income

    user_profile["household_size"] = household_size

    session["user_profile"] = user_profile



    return jsonify(result)



@app.route("/reset", methods=["POST"])

def reset():

    session["conversation_history"] = []

    session["last_topic"] = ""

    session["last_state"] = None

    session["user_profile"] = {

        "state": None, "income": None, "household_size": None,

        "age": None, "life_events": [], "has_insurance": None

    }

    return jsonify({"status": "cleared"})



if __name__ == "__main__":

    app.run(debug=True, port=5000)