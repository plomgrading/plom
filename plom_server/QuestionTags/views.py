# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import render, redirect
from QuestionTags.services import get_question_labels, add_question_tag as add_tag
from .models import QuestionTag, Tag

def qtags_landing(request):
    question_labels = get_question_labels()
    question_tags = QuestionTag.objects.all()
    context = {
        "question_labels": question_labels,
        "question_count": len(question_labels),
        "question_tags": question_tags,
    }
    return render(request, 'Questiontags/qtags_landing.html', context)

def add_question_tag(request):
    if request.method == 'POST':
        question_number = request.POST.get('questionNumber')
        description = request.POST.get('description')
        add_tag(question_number, description)
        return redirect('qtags_landing')
    return redirect('qtags_landing')

def create_tag(request):
    if request.method == 'POST':
        tag_name = request.POST.get('tagName')
        description = request.POST.get('tagDescription')
        Tag.objects.create(tag_name=tag_name, description=description)
        return redirect('qtags_landing')
    return redirect('qtags_landing')