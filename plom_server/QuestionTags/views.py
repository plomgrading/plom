# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import render, redirect
from QuestionTags.services.questiontag_service import get_question_labels

def qtags_landing(request):
    question_labels = get_question_labels()
    context = {
        "question_labels": question_labels,
        "question_count": len(question_labels)
    }
    return render(request, 'Questiontags/qtags_landing.html', context)

def add_question_tag(request):
    if request.method == 'POST':
        question_number = request.POST.get('questionNumber')
        description = request.POST.get('description')
        # Handle saving the data here. For now, we'll just print it.
        print(f'Question Number: {question_number}, Description: {description}')
        # Redirect back to the question tags landing page
        return redirect('qtags_landing')
    return redirect('qtags_landing')
