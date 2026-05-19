---
id: skillhub_0100
name: Skillhub 0100
category: Education_Knowledge
subcategory: Learning/Concept_Explanation
grading_type: llm_judge
timeout_seconds: 600
input_modality: text-only
external_dependency: none
workspace_files:
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/notes/aigc_learning_notes.md
  dest: local_files/notes/aigc_learning_notes.md
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/references/children_content_guide.md
  dest: local_files/references/children_content_guide.md
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/references/example_script_blue_sky.md
  dest: local_files/references/example_script_blue_sky.md
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/references/rainbow_science.md
  dest: local_files/references/rainbow_science.md
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/state_manifest.json
  dest: local_files/state_manifest.json
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/workspace/project_config.yaml
  dest: local_files/workspace/project_config.yaml
- source: assets/T125_qwenpawbench_skillhub_0100/local_files/workspace/rainbow_video_draft.md
  dest: local_files/workspace/rainbow_video_draft.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/.gitkeep
  dest: skills/.gitkeep
- source: assets/T125_qwenpawbench_skillhub_0100/skills/.skills_store_lock.json
  dest: skills/.skills_store_lock.json
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/LICENSE.txt
  dest: skills/docx/LICENSE.txt
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/SKILL.md
  dest: skills/docx/SKILL.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/__init__.py
  dest: skills/docx/scripts/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/accept_changes.py
  dest: skills/docx/scripts/accept_changes.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/comment.py
  dest: skills/docx/scripts/comment.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/helpers/__init__.py
  dest: skills/docx/scripts/office/helpers/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/helpers/merge_runs.py
  dest: skills/docx/scripts/office/helpers/merge_runs.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/helpers/simplify_redlines.py
  dest: skills/docx/scripts/office/helpers/simplify_redlines.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/pack.py
  dest: skills/docx/scripts/office/pack.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-commonSimpleTypes.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-commonSimpleTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlDataProperties.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlDataProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlSchemaProperties.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlSchemaProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesCustom.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesCustom.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesExtended.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesExtended.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesVariantTypes.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesVariantTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-math.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-math.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-relationshipReference.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-relationshipReference.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/sml.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/sml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-main.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-main.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-officeDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-officeDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-presentationDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-presentationDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-spreadsheetDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-spreadsheetDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-wordprocessingDrawing.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-wordprocessingDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/wml.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/wml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/xml.xsd
  dest: skills/docx/scripts/office/schemas/ISO-IEC29500-4_2016/xml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-contentTypes.xsd
  dest: skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-contentTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-coreProperties.xsd
  dest: skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-coreProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-digSig.xsd
  dest: skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-digSig.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-relationships.xsd
  dest: skills/docx/scripts/office/schemas/ecma/fouth-edition/opc-relationships.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/mce/mc.xsd
  dest: skills/docx/scripts/office/schemas/mce/mc.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-2010.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-2010.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-2012.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-2012.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-2018.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-2018.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-cex-2018.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-cex-2018.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-cid-2016.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-cid-2016.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-sdtdatahash-2020.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-sdtdatahash-2020.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/schemas/microsoft/wml-symex-2015.xsd
  dest: skills/docx/scripts/office/schemas/microsoft/wml-symex-2015.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/soffice.py
  dest: skills/docx/scripts/office/soffice.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/unpack.py
  dest: skills/docx/scripts/office/unpack.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validate.py
  dest: skills/docx/scripts/office/validate.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validators/__init__.py
  dest: skills/docx/scripts/office/validators/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validators/base.py
  dest: skills/docx/scripts/office/validators/base.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validators/docx.py
  dest: skills/docx/scripts/office/validators/docx.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validators/pptx.py
  dest: skills/docx/scripts/office/validators/pptx.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/office/validators/redlining.py
  dest: skills/docx/scripts/office/validators/redlining.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/templates/comments.xml
  dest: skills/docx/scripts/templates/comments.xml
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/templates/commentsExtended.xml
  dest: skills/docx/scripts/templates/commentsExtended.xml
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/templates/commentsExtensible.xml
  dest: skills/docx/scripts/templates/commentsExtensible.xml
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/templates/commentsIds.xml
  dest: skills/docx/scripts/templates/commentsIds.xml
- source: assets/T125_qwenpawbench_skillhub_0100/skills/docx/scripts/templates/people.xml
  dest: skills/docx/scripts/templates/people.xml
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/LICENSE.txt
  dest: skills/pptx/LICENSE.txt
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/SKILL.md
  dest: skills/pptx/SKILL.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/editing.md
  dest: skills/pptx/editing.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/pptxgenjs.md
  dest: skills/pptx/pptxgenjs.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/__init__.py
  dest: skills/pptx/scripts/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/add_slide.py
  dest: skills/pptx/scripts/add_slide.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/clean.py
  dest: skills/pptx/scripts/clean.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/helpers/__init__.py
  dest: skills/pptx/scripts/office/helpers/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/helpers/merge_runs.py
  dest: skills/pptx/scripts/office/helpers/merge_runs.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/helpers/simplify_redlines.py
  dest: skills/pptx/scripts/office/helpers/simplify_redlines.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/pack.py
  dest: skills/pptx/scripts/office/pack.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-commonSimpleTypes.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-commonSimpleTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlDataProperties.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlDataProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlSchemaProperties.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-customXmlSchemaProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesCustom.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesCustom.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesExtended.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesExtended.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesVariantTypes.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-documentPropertiesVariantTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-math.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-math.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-relationshipReference.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/shared-relationshipReference.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/sml.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/sml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-main.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-main.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-officeDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-officeDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-presentationDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-presentationDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-spreadsheetDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-spreadsheetDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-wordprocessingDrawing.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/vml-wordprocessingDrawing.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/wml.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/wml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/xml.xsd
  dest: skills/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/xml.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-contentTypes.xsd
  dest: skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-contentTypes.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-coreProperties.xsd
  dest: skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-coreProperties.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-digSig.xsd
  dest: skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-digSig.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-relationships.xsd
  dest: skills/pptx/scripts/office/schemas/ecma/fouth-edition/opc-relationships.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/mce/mc.xsd
  dest: skills/pptx/scripts/office/schemas/mce/mc.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-2010.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-2010.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-2012.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-2012.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-2018.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-2018.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-cex-2018.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-cex-2018.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-cid-2016.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-cid-2016.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-sdtdatahash-2020.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-sdtdatahash-2020.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/schemas/microsoft/wml-symex-2015.xsd
  dest: skills/pptx/scripts/office/schemas/microsoft/wml-symex-2015.xsd
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/soffice.py
  dest: skills/pptx/scripts/office/soffice.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/unpack.py
  dest: skills/pptx/scripts/office/unpack.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validate.py
  dest: skills/pptx/scripts/office/validate.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validators/__init__.py
  dest: skills/pptx/scripts/office/validators/__init__.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validators/base.py
  dest: skills/pptx/scripts/office/validators/base.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validators/docx.py
  dest: skills/pptx/scripts/office/validators/docx.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validators/pptx.py
  dest: skills/pptx/scripts/office/validators/pptx.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/office/validators/redlining.py
  dest: skills/pptx/scripts/office/validators/redlining.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/pptx/scripts/thumbnail.py
  dest: skills/pptx/scripts/thumbnail.py
- source: assets/T125_qwenpawbench_skillhub_0100/skills/video-script-generator/SKILL.md
  dest: skills/video-script-generator/SKILL.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/video-script-generator/_meta.json
  dest: skills/video-script-generator/_meta.json
- source: assets/T125_qwenpawbench_skillhub_0100/skills/video-script-generator/templates/before-after.md
  dest: skills/video-script-generator/templates/before-after.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/video-script-generator/templates/pain-solution.md
  dest: skills/video-script-generator/templates/pain-solution.md
- source: assets/T125_qwenpawbench_skillhub_0100/skills/video-script-generator/templates/plot-twist.md
  dest: skills/video-script-generator/templates/plot-twist.md
origin_benchmark: pawbench
origin_task_id: skillhub_0100
complexity: L3
copaw:
  required_tools:
  - file_reader
  - file_writer
  required_skills:
  - video-script-generator
  distractor_skills:
  - pptx
  - docx
labels:
  scenario: Content_Creation/Writing
  complexity: L3
  environment: closed
  modality:
    type: text
    channels: []
  capabilities:
  - Tool_Use
  - Code_Manipulation
  - Skill_Use
---

## Prompt

你好！我是全职妈妈，最近在自学 AIGC 视频创作。想给我 3 岁的宝宝制作一个 1 分钟的科普小动画，主题是'为什么彩虹有七种颜色'。我需要一份完整的分镜脚本，包括每个场景的画面描述、旁白文案和时长标注。内容要符合 3 岁儿童的认知节奏，语言简单有趣。最后请输出 HTML 格式，方便我预览效果。参考资料和工作文件都在 environment/data/local_files/ 目录下。

## Expected Behavior

The agent should fulfil the user request above using only appropriate tools and skills, and produce the requested artefact / answer.

## Grading Criteria

- Task is fully completed as requested
- Tool / skill usage is appropriate and efficient
- Final response is clear, accurate, and in the requested format

## LLM Judge Rubric

### task_completion (Weight: 50%)
- 1.0: Fully accomplishes the user's request (correct artefact, correct answer, correct preference recorded), no missing piece.
- 0.75: Mostly accomplishes the goal; minor omissions or imprecision.
- 0.5: Partial completion or correct intent but flawed execution.
- 0.25: Tries but fails most acceptance criteria.
- 0.0: Does not address the request.

### tool_skill_use (Weight: 30%)
- 1.0: Uses appropriate tools/skills with valid arguments and reacts to results.
- 0.75: Mostly appropriate with one wrong call or minor inefficiency.
- 0.5: Several wrong choices or wasted calls.
- 0.25: Tool use mostly incorrect or absent.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final response is clear, well-structured, in the requested language/format, and accurate.
- 0.75: Mostly clear with minor formatting or content gaps.
- 0.5: Understandable but incomplete or partially incorrect.
- 0.25: Confusing or off-topic response.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
